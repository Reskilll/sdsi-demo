/**
 * Hierarchical source code indexer: generates and maintains a two-tier Markdown
 * index of the codebase under `.masterx/`, mapping high-level architecture to
 * low-level implementation files.
 *
 *   .masterx/index.md         High-Level Design + feature links to ./docs/*.md
 *   .masterx/docs/<slug>.md   Low-Level Design + file registry with a strict
 *                             one-line description per source file
 *   .masterx/changes.md       source changes recorded by the Verify stage;
 *                             consumed and cleared by the next Scout run
 */
import * as path from 'path';
import * as vscode from 'vscode';

/** Folder (under the workspace root) holding the generated index. */
export const INDEX_DIR = '.masterx';

/** Cap on existing index content echoed back to the Worker on updates. */
const EXISTING_INDEX_CAP = 40_000;

/** One feature page of the index. */
export interface IndexFeature {
  name: string;
  /** File name for `docs/<slug>.md` (sanitized on write). */
  slug: string;
  /** Feature-specific Low-Level Design (Markdown). */
  lld: string;
  /** File registry: every source file with its one-line responsibility. */
  files: Array<{ path: string; description: string }>;
}

/** The two-tier index content produced by the Scout stage. */
export interface IndexArtifacts {
  /** System-wide High-Level Design (Markdown). */
  hld: string;
  features: IndexFeature[];
}

/** Whatever already exists under `.masterx/` before a Scout run. */
export interface IndexState {
  exists: boolean;
  indexMd: string;
  featureDocs: string;
  changesMd: string;
}

function indexFile(root: string): vscode.Uri {
  return vscode.Uri.file(path.join(root, INDEX_DIR, 'index.md'));
}

function docsDir(root: string): vscode.Uri {
  return vscode.Uri.file(path.join(root, INDEX_DIR, 'docs'));
}

function changesFile(root: string): vscode.Uri {
  return vscode.Uri.file(path.join(root, INDEX_DIR, 'changes.md'));
}

async function readFileSafe(uri: vscode.Uri): Promise<string> {
  try {
    return Buffer.from(await vscode.workspace.fs.readFile(uri)).toString('utf8');
  } catch {
    return '';
  }
}

/** Normalize a feature name into a safe `docs/<slug>.md` file name. */
export function slugify(name: string): string {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || 'feature';
}

/**
 * Check `.masterx/` before any source reading: returns the existing index
 * content when present so the Scout can update instead of regenerate.
 */
export async function loadIndexState(root: string): Promise<IndexState> {
  const indexMd = await readFileSafe(indexFile(root));
  if (!indexMd.trim()) {
    return { exists: false, indexMd: '', featureDocs: '', changesMd: '' };
  }

  let featureDocs = '';
  try {
    const entries = await vscode.workspace.fs.readDirectory(docsDir(root));
    const names = entries
      .filter(([name, type]) => type === vscode.FileType.File && name.endsWith('.md'))
      .map(([name]) => name)
      .sort();
    for (const name of names) {
      const content = await readFileSafe(vscode.Uri.joinPath(docsDir(root), name));
      featureDocs += `\n\n--- docs/${name} ---\n${content}`;
      if (featureDocs.length >= EXISTING_INDEX_CAP) {
        break;
      }
    }
  } catch {
    // No docs directory yet.
  }

  return {
    exists: true,
    indexMd: indexMd.slice(0, EXISTING_INDEX_CAP),
    featureDocs: featureDocs.slice(0, EXISTING_INDEX_CAP),
    changesMd: await readFileSafe(changesFile(root)),
  };
}

/** Write the two-tier index and drop feature pages that are no longer linked. */
export async function writeIndex(root: string, artifacts: IndexArtifacts): Promise<string[]> {
  const written: string[] = [];
  const docs = docsDir(root);
  await vscode.workspace.fs.createDirectory(docs);

  const wanted = new Set<string>();
  const links: string[] = [];
  for (const feature of artifacts.features) {
    const slug = slugify(feature.slug || feature.name);
    wanted.add(`${slug}.md`);
    links.push(`- [${feature.name}](./docs/${slug}.md)`);

    const registry = feature.files.map((f) => `- \`${f.path}\` — ${f.description}`).join('\n');
    const page =
      `# ${feature.name}\n\n` +
      `## Low-Level Design\n\n${feature.lld.trim()}\n\n` +
      `## File Registry\n\n${registry}\n`;
    await vscode.workspace.fs.writeFile(
      vscode.Uri.joinPath(docs, `${slug}.md`),
      Buffer.from(page, 'utf8')
    );
    written.push(`${INDEX_DIR}/docs/${slug}.md`);
  }

  const index =
    `# High-Level Design\n\n${artifacts.hld.trim()}\n\n` +
    `# Features\n\n${links.join('\n')}\n`;
  await vscode.workspace.fs.writeFile(indexFile(root), Buffer.from(index, 'utf8'));
  written.unshift(`${INDEX_DIR}/index.md`);

  try {
    const entries = await vscode.workspace.fs.readDirectory(docs);
    for (const [name, type] of entries) {
      if (type === vscode.FileType.File && name.endsWith('.md') && !wanted.has(name)) {
        await vscode.workspace.fs.delete(vscode.Uri.joinPath(docs, name));
      }
    }
  } catch {
    // Nothing to clean up.
  }

  return written;
}

/** Append one execution's change record to `.masterx/changes.md`. */
export async function writeChanges(root: string, section: string): Promise<void> {
  const existing = (await readFileSafe(changesFile(root))).trimEnd();
  const text = existing ? `${existing}\n\n${section.trim()}\n` : `${section.trim()}\n`;
  await vscode.workspace.fs.createDirectory(vscode.Uri.file(path.join(root, INDEX_DIR)));
  await vscode.workspace.fs.writeFile(changesFile(root), Buffer.from(text, 'utf8'));
}

/** Clear the pending-change record once the Scout has incorporated it. */
export async function clearChanges(root: string): Promise<void> {
  try {
    await vscode.workspace.fs.delete(changesFile(root));
  } catch {
    // Already absent.
  }
}
