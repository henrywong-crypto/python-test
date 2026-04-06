// Showcase: every TypeScript construct supported by convert-typescript-to-rust

// ===== Variables & Constants =====
const name: string = "hello";
let count: number = 42;
let active: boolean = true;
const PI: number = 3.14159;

// ===== Interfaces =====
interface User {
  name: string;
  age: number;
  email?: string;
}

interface Config {
  // Server settings
  host: string;
  port: number;
  debug: boolean;
}

// ===== Classes =====
class Animal {
  name: string;
  sound: string;

  constructor(name: string, sound: string) {
    this.name = name;
    this.sound = sound;
  }

  speak(): string {
    return `${this.name} says ${this.sound}`;
  }
}

// ===== Enums =====
enum Color {
  Red,
  Green,
  Blue,
}

// ===== Type Aliases =====
type StringOrNumber = string | number;
type UserMap = Map<string, User>;
type IdList = Array<number>;
type Nullable<T> = T | null;
type UserRecord = Record<string, User>;

// ===== Functions =====
function add(a: number, b: number): number {
  return a + b;
}

export async function fetchData(url: string): Promise<string> {
  const response = await fetch(url);
  return response.text();
}

const multiply = (x: number, y: number) => x * y;

// ===== Control Flow =====
function process(value: number): string {
  if (value > 100) {
    return "high";
  } else if (value > 50) {
    return "medium";
  } else {
    return "low";
  }
}

// ===== Switch =====
function describe(status: number): string {
  switch (status) {
    case 200:
      return "OK";
    case 404:
      return "Not Found";
    default:
      return "Unknown";
  }
}

// ===== Loops =====
function loopExamples(): void {
  const items = [1, 2, 3];
  for (const item of items) {
    console.log(item);
  }

  let x = 0;
  while (x < 5) {
    x++;
  }

  let y = 0;
  do {
    y++;
  } while (y < 3);
}

// ===== Try/Catch =====
async function safeFetch(url: string): Promise<string | null> {
  try {
    const resp = await fetch(url);
    return resp.text();
  } catch (err) {
    console.error("Fetch failed:", err);
    return null;
  } finally {
    console.log("done");
  }
}

// ===== Destructuring =====
function destructuringExample(): void {
  const { name, age } = getUser();
  const [first, second] = getItems();
}

// ===== Template Strings =====
function formatMessage(user: string, count: number): string {
  return `Hello ${user}, you have ${count} new messages`;
}

const simple = `no interpolation here`;

// ===== Objects & Spread =====
const config = {
  host: "localhost",
  port: 8080,
  debug: true,
};

const merged = { ...defaults, ...overrides, extra: "value" };

// ===== Arrow Functions =====
const double = (x: number) => x * 2;
const noop = () => {};
const numbers = [1, 2, 3];
const doubled = numbers.map((n) => n * 2);
const filtered = numbers.filter((n) => n > 1);

// ===== Ternary =====
const result = active ? "yes" : "no";

// ===== Standard Library: Math =====
function mathExamples(): void {
  const a = Math.floor(3.7);
  const b = Math.ceil(3.2);
  const c = Math.round(3.5);
  const d = Math.abs(-5);
  const e = Math.sqrt(16);
  const f = Math.pow(2, 10);
  const g = Math.random();
  const h = Math.max(1, 2);
  const i = Math.min(1, 2);
}

// ===== Standard Library: Console =====
function consoleExamples(): void {
  console.log("info");
  console.warn("warning");
  console.error("error");
  console.debug("debug");
}

// ===== Standard Library: JSON =====
function jsonExamples(): void {
  const str = JSON.stringify({ key: "value" });
  const obj = JSON.parse(str);
}

// ===== Standard Library: Other =====
function otherExamples(): void {
  const now = Date.now();
  const keys = Object.keys(obj);
  const values = Object.values(obj);
  const entries = Object.entries(obj);
  const num = parseInt("42");
  const float = parseFloat("3.14");
  const fixed = (3.14159).toFixed(2);
}

// ===== Standard Library: String Methods =====
function stringExamples(): void {
  const s = "hello world";
  const upper = s.toUpperCase();
  const lower = s.toLowerCase();
  const trimmed = s.trim();
  const parts = s.split(" ");
  const has = s.includes("world");
  const replaced = s.replace("world", "rust");
  const len = s.length;
}

// ===== Standard Library: Array Methods =====
function arrayExamples(): void {
  const arr = [1, 2, 3];
  arr.push(4);
  const joined = arr.join(", ");
  const mapped = arr.map((x) => x * 2);
  const filtered = arr.filter((x) => x > 1);
  const found = arr.find((x) => x === 2);
  const every = arr.every((x) => x > 0);
  const some = arr.some((x) => x > 2);
  const len = arr.length;
}

// ===== Exports =====
export const API_URL = "https://api.example.com";
export type UserId = string;
export interface Options {
  verbose: boolean;
  timeout: number;
}
