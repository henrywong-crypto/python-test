//! Converted from examples/input.ts

// Showcase: every TypeScript construct supported by convert-typescript-to-rust
// ===== Variables & Constants =====
let name: String = "hello";

let mut count: f64 = 42;

let mut active: bool = true;

let pi: f64 = 3.14159;

// ===== Interfaces =====
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
    pub debug: bool,
}

// ===== Classes =====
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

// ===== Enums =====
#[derive(Debug, Clone, PartialEq)]
pub enum Color {
    Red,
    Green,
    Blue,
}

// ===== Type Aliases =====
pub type StringOrNumber = serde_json::Value;

pub type UserMap = std::collections::HashMap<String, User>;

pub type IdList = Vec<f64>;

pub type Nullable = Option<T>;

pub type UserRecord = std::collections::HashMap<String, User>;

// ===== Functions =====
pub fn add(a: f64, b: f64) -> f64 {
    return a + b;
}

pub async fn fetch_data(url: &str) -> String {
    let response = fetch(url).await;
    return response.text();
}

let multiply = |x, y| x * y;

// ===== Control Flow =====
pub fn process(value: f64) -> String {
    if value > 100 {
        return "high";
    } else if value > 50 {
        return "medium";
    } else {
        return "low";
    }
}

// ===== Switch =====
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

// ===== Loops =====
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

// ===== Try/Catch =====
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

// ===== Destructuring =====
pub fn destructuring_example() {
    let _destructured = get_user();
    let name = _destructured.get("name").cloned().unwrap_or_default();
    let age = _destructured.get("age").cloned().unwrap_or_default();
    let _arr = get_items();
    let first = _arr.get(0).cloned().unwrap_or_default();
    let second = _arr.get(1).cloned().unwrap_or_default();
}

// ===== Template Strings =====
pub fn format_message(user: &str, count: f64) -> String {
    return format!("Hello {}, you have {} new messages", user, count);
}

let simple = "no interpolation here".to_string();

// ===== Objects & Spread =====
let config = serde_json::json!({"host": "localhost", "port": 8080, "debug": true});

let merged = serde_json::json!({..defaults, ..overrides, "extra": "value"});

// ===== Arrow Functions =====
let double = |x| x * 2;

let noop = || {

};

let numbers = vec![1, 2, 3];

let doubled = numbers.iter().map(|n| n * 2);

let filtered = numbers.iter().filter(|n| n > 1);

// ===== Ternary =====
let result = if active { "yes" } else { "no" };

// ===== Standard Library: Math =====
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

// ===== Standard Library: Console =====
pub fn console_examples() {
    tracing::info!("{}", "info");
    tracing::warn!("{}", "warning");
    tracing::error!("{}", "error");
    tracing::debug!("{}", "debug");
}

// ===== Standard Library: JSON =====
pub fn json_examples() {
    let str = serde_json::to_string(&serde_json::json!({"key": "value"})).unwrap_or_default();
    let obj = serde_json::from_str(str).unwrap_or_default();
}

// ===== Standard Library: Other =====
pub fn other_examples() {
    let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis() as f64;
    let keys = obj.keys().cloned().collect::<Vec<_>>();
    let values = obj.values().cloned().collect::<Vec<_>>();
    let entries = obj.iter().collect::<Vec<_>>();
    let num = "42".parse::<i64>().unwrap_or(0);
    let float = "3.14".parse::<f64>().unwrap_or(0.0);
    let fixed = format!("{:.2}", (3.14159));
}

// ===== Standard Library: String Methods =====
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

// ===== Standard Library: Array Methods =====
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

// ===== Exports =====
pub const API_URL: &str = "https://api.example.com";

pub type UserId = String;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Options {
    pub verbose: bool,
    pub timeout: f64,
}