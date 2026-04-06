# Conversion Gallery

Every supported TypeScript construct with its **actual converter output**.

---

## 1. Variables & Constants

**TypeScript:**
```typescript
const name: string = "hello";
let count: number = 42;
let active: boolean = true;
const PI: number = 3.14159;
var legacy: any = null;
```

**Rust (actual output):**
```rust
let name: String = "hello";

let mut count: f64 = 42;

let mut active: bool = true;

let pi: f64 = 3.14159;

let mut legacy: serde_json::Value = None;
```

---

## 2. Functions

**TypeScript:**
```typescript
function add(a: number, b: number): number {
  return a + b;
}

export async function fetchData(url: string): Promise<string> {
  const response = await fetch(url);
  return response.text();
}

const multiply = (x: number, y: number) => x * y;

function greet(name: string = "World"): void {
  console.log(`Hello, ${name}!`);
}

function sum(...nums: number[]): number {
  return nums.reduce((a, b) => a + b, 0);
}
```

**Rust (actual output):**
```rust
pub fn add(a: f64, b: f64) -> f64 {
    return a + b;
}

pub async fn fetch_data(url: &str) -> String {
    let response = fetch(url).await;
    return response.text();
}

let multiply = |x, y| x * y;

pub fn greet(name: &str) {
    tracing::info!("{}", format!("Hello, {}!", name));
}

pub fn sum(nums: &[Vec<f64>]) -> f64 {
    return nums.reduce(|a, b| a + b, 0);
}
```

---

## 3. Interfaces -> Structs

**TypeScript:**
```typescript
interface User {
  name: string;
  age: number;
  email?: string;
}

interface Config {
  // Server settings
  host: string;
  port: number;
  /** Whether to enable debug mode */
  debug: boolean;
}
```

**Rust (actual output):**
```rust
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct User {
    pub name: String,
    pub age: f64,
    pub email: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Config {
    // Server settings
    pub host: String,
    pub port: f64,
    /** Whether to enable debug mode */
    pub debug: bool,
}
```

---

## 4. Classes -> Structs + Impl

**TypeScript:**
```typescript
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
```

**Rust (actual output):**
```rust
pub struct Animal {
    pub name: String,
    pub sound: String,
}

impl Animal {
    pub fn new(&self, name: &str, sound: &str) {
        self.sound = sound;
    }

    pub fn speak(&self) -> String {
        return format!("{} says {}", self.name, self.sound);
    }
}
```

---

## 5. Enums

**TypeScript:**
```typescript
enum Color {
  Red,
  Green,
  Blue,
}
```

**Rust (actual output):**
```rust
#[derive(Debug, Clone, PartialEq)]
pub enum Color {
    Red,
    Green,
    Blue,
}
```

---

## 6. Type Aliases

**TypeScript:**
```typescript
type StringOrNumber = string | number;
type UserMap = Map<string, User>;
type IdList = Array<number>;
type Nullable<T> = T | null;
type UserRecord = Record<string, User>;
type ReadonlyUser = Readonly<User>;
type PartialConfig = Partial<Config>;
```

**Rust (actual output):**
```rust
pub type StringOrNumber = serde_json::Value;

pub type UserMap = std::collections::HashMap<String, User>;

pub type IdList = Vec<f64>;

pub type Nullable = Option<T>;

pub type UserRecord = std::collections::HashMap<String, User>;

pub type ReadonlyUser = User;

pub type PartialConfig = Config;
```

---

## 7. Control Flow (if/else)

**TypeScript:**
```typescript
function process(value: number): string {
  if (value > 100) {
    return "high";
  } else if (value > 50) {
    return "medium";
  } else {
    return "low";
  }
}
```

**Rust (actual output):**
```rust
pub fn process(value: f64) -> String {
    if value > 100 {
        return "high";
    } else if value > 50 {
        return "medium";
    } else {
        return "low";
    }
}
```

---

## 8. Loops

**TypeScript:**
```typescript
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
```

**Rust (actual output):**
```rust
pub fn loop_examples() {
    let items = vec![1, 2, 3];
    for _item in items.iter() {
        tracing::info!("{}", item);
    }
    let mut x = 0;
    while x < 5 {
        { let _v = x; x += 1; _v };
    }
    let mut y = 0;
    loop {
        { let _v = y; y += 1; _v };
        if !(y < 3) {
            break;
        }
    }
}
```

---

## 9. Switch -> Match

**TypeScript:**
```typescript
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
```

**Rust (actual output):**
```rust
pub fn describe(status: f64) -> String {
    match status {
        200 => {
            return "OK";
        }
        404 => {
            return "Not Found";
        }
        _ => {
            return "Unknown";
        }
    }
}
```

---

## 10. Try/Catch -> Match Result

**TypeScript:**
```typescript
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
```

**Rust (actual output):**
```rust
pub async fn safe_fetch(url: &str) -> Option<String> {
    match (|| -> Result<(), Box<dyn std::error::Error>> {
        let resp = fetch(url).await;
        return resp.text();
        Ok(())
    })() {
        Ok(()) => {}
        Err(err) => {
            tracing::error!("{}", "Fetch failed:", err);
            return None;
        }
    }
    // finally
    tracing::info!("{}", "done");
}
```

---

## 11. Destructuring

**TypeScript:**
```typescript
function example(): void {
  const { name, age } = getUser();
  const [first, second] = getItems();
}
```

**Rust (actual output):**
```rust
pub fn example() {
    let _destructured = get_user();
    let name = _destructured.get("name").cloned().unwrap_or_default();
    let age = _destructured.get("age").cloned().unwrap_or_default();
    let _arr = get_items();
    let first = _arr.get(0).cloned().unwrap_or_default();
    let second = _arr.get(1).cloned().unwrap_or_default();
}
```

---

## 12. Template Strings -> format!()

**TypeScript:**
```typescript
function formatMessage(user: string, count: number): string {
  return `Hello ${user}, you have ${count} new messages`;
}

const simple = `no interpolation here`;
```

**Rust (actual output):**
```rust
pub fn format_message(user: &str, count: f64) -> String {
    return format!("Hello {}, you have {} new messages", user, count);
}

let simple = "no interpolation here".to_string();
```

---

## 13. Objects & Spread

**TypeScript:**
```typescript
const config = {
  host: "localhost",
  port: 8080,
  debug: true,
};

const merged = { ...defaults, ...overrides, extra: "value" };

function makeHeaders(token: string): object {
  return {
    ...getDefaultHeaders(),
    "Authorization": token,
  };
}
```

**Rust (actual output):**
```rust
let config = serde_json::json!({"host": "localhost", "port": 8080, "debug": true});

let merged = serde_json::json!({..defaults, ..overrides, "extra": "value"});

pub fn make_headers(token: &str) -> serde_json::Value {
    return serde_json::json!({..get_default_headers(), "Authorization": token});
}
```

---

## 14. Arrow Functions -> Closures

**TypeScript:**
```typescript
const double = (x: number) => x * 2;
const noop = () => {};
const numbers = [1, 2, 3];
const doubled = numbers.map((n) => n * 2);
const filtered = numbers.filter((n) => n > 1);
```

**Rust (actual output):**
```rust
let double = |x| x * 2;

let noop = || {

};

let numbers = vec![1, 2, 3];

let doubled = numbers.iter().map(|n| n * 2);

let filtered = numbers.iter().filter(|n| n > 1);
```

---

## 15. Async/Await

**TypeScript:**
```typescript
async function loadUser(id: string): Promise<User> {
  const response = await fetch(`/api/users/${id}`);
  const data = await response.json();
  return data as User;
}
```

**Rust (actual output):**
```rust
pub async fn load_user(id: &str) -> User {
    let response = fetch(format!("/api/users/{}", id)).await;
    let data = response.json().await;
    return data;
}
```

---

## 16. Ternary -> if Expression

**TypeScript:**
```typescript
const result = condition ? "yes" : "no";
const value = x > 0 ? x : -x;
```

**Rust (actual output):**
```rust
let result = if condition { "yes" } else { "no" };

let value = if x > 0 { x } else { -x };
```

---

## 17. Math.*

**TypeScript:**
```typescript
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
```

**Rust (actual output):**
```rust
pub fn math_examples() {
    let a = (3.7 as f64).floor();
    let b = (3.2 as f64).ceil();
    let c = (3.5 as f64).round();
    let d = (-5 as f64).abs();
    let e = (16 as f64).sqrt();
    let f = (2 as f64).powf(10 as f64);
    let g = rand::random::<f64>();
    let h = (1 as f64).max(2 as f64);
    let i = (1 as f64).min(2 as f64);
}
```

---

## 18. console.* -> tracing::*

**TypeScript:**
```typescript
function consoleExamples(): void {
  console.log("info");
  console.warn("warning");
  console.error("error");
  console.debug("debug");
}
```

**Rust (actual output):**
```rust
pub fn console_examples() {
    tracing::info!("{}", "info");
    tracing::warn!("{}", "warning");
    tracing::error!("{}", "error");
    tracing::debug!("{}", "debug");
}
```

---

## 19. JSON.* -> serde_json::*

**TypeScript:**
```typescript
function jsonExamples(): void {
  const str = JSON.stringify({ key: "value" });
  const obj = JSON.parse(str);
}
```

**Rust (actual output):**
```rust
pub fn json_examples() {
    let str = serde_json::to_string(&serde_json::json!({"key": "value"})).unwrap_or_default();
    let obj = serde_json::from_str(str).unwrap_or_default();
}
```

---

## 20. Date/Object/parseInt

**TypeScript:**
```typescript
function otherExamples(): void {
  const now = Date.now();
  const keys = Object.keys(obj);
  const values = Object.values(obj);
  const entries = Object.entries(obj);
  const num = parseInt("42");
  const float = parseFloat("3.14");
  const fixed = (3.14159).toFixed(2);
}
```

**Rust (actual output):**
```rust
pub fn other_examples() {
    let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis() as f64;
    let keys = obj.keys().cloned().collect::<Vec<_>>();
    let values = obj.values().cloned().collect::<Vec<_>>();
    let entries = obj.iter().collect::<Vec<_>>();
    let num = "42".parse::<i64>().unwrap_or(0);
    let float = "3.14".parse::<f64>().unwrap_or(0.0);
    let fixed = format!("{:.2}", (3.14159));
}
```

---

## 21. String Methods

**TypeScript:**
```typescript
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
```

**Rust (actual output):**
```rust
pub fn string_examples() {
    let s = "hello world";
    let upper = s.to_uppercase();
    let lower = s.to_lowercase();
    let trimmed = s.trim();
    let parts = s.split(" ");
    let has = s.contains("world");
    let replaced = s.replace("world", "rust");
    let len = s.len();
}
```

---

## 22. Array Methods

**TypeScript:**
```typescript
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
```

**Rust (actual output):**
```rust
pub fn array_examples() {
    let arr = vec![1, 2, 3];
    arr.push(4);
    let joined = arr.join(", ");
    let mapped = arr.iter().map(|x| x * 2);
    let filtered = arr.iter().filter(|x| x > 1);
    let found = arr.iter().find(|x| x == 2);
    let every = arr.iter().all(|x| x > 0);
    let some = arr.iter().any(|x| x > 2);
    let len = arr.len();
}
```

---

## 23. Comments (Preserved)

**TypeScript:**
```typescript
// Single line comment
const x = 1;

/* Multi-line
   comment */
const y = 2;

/** JSDoc comment */
function greet(name: string): string {
  return name; // inline comment
}

enum Status {
  // Active status
  Active,
  // Inactive status
  Inactive,
}
```

**Rust (actual output):**
```rust
// Single line comment
let x = 1;

/* Multi-line
   comment */
let y = 2;

/** JSDoc comment */
pub fn greet(name: &str) -> String {
    return name;
    // inline comment
}

#[derive(Debug, Clone, PartialEq)]
pub enum Status {
    // Active status
    Active,
    // Inactive status
    Inactive,
}
```

---

## 24. Exports

**TypeScript:**
```typescript
export const API_URL = "https://api.example.com";
export type UserId = string;
export interface Options {
  verbose: boolean;
  timeout: number;
}
```

**Rust (actual output):**
```rust
pub const API_URL: &str = "https://api.example.com";

pub type UserId = String;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Options {
    pub verbose: bool,
    pub timeout: f64,
}
```
