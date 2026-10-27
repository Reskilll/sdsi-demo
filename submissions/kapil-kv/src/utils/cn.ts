type ClassValue = string | undefined | null | false | ClassValue[];

function toVal(mix: ClassValue): string {
  if (typeof mix === "string") return mix;
  if (Array.isArray(mix)) {
    let str = "";
    for (const item of mix) {
      const val = toVal(item);
      if (val) str += (str ? " " : "") + val;
    }
    return str;
  }
  return "";
}

export function cn(...inputs: ClassValue[]): string {
  let str = "";
  for (const input of inputs) {
    const val = toVal(input);
    if (val) str += (str ? " " : "") + val;
  }
  return str;
}