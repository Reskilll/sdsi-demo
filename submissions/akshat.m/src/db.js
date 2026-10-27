import { readFile, writeFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = join(dirname(fileURLToPath(import.meta.url)), '..', 'data');

/**
 * @template T
 * @param {string} file
 * @returns {Promise<T>}
 */
async function load(file) {
  try {
    const raw = await readFile(join(DATA, file), 'utf-8');
    return JSON.parse(raw);
  } catch {
    return /** @type {T} */ ([]);
  }
}

/**
 * @param {string} file
 * @param {*} data
 */
async function save(file, data) {
  await writeFile(join(DATA, file), JSON.stringify(data, null, 2), 'utf-8');
}

export function loadRooms()  { return load('rooms.json'); }
export function loadBookings() { return load('bookings.json'); }
export function saveBookings(b) { return save('bookings.json', b); }