//! Converted from examples/input.ts


// Sample TypeScript file demonstrating key features
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct User {
    pub name: String,
    pub age: f64,
    pub email: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Status {
    Active,
    Inactive,
    // Pending status
    Pending,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Config {
    pub host: String,
    pub port: f64,
    pub debug: Option<bool>,
}

pub const MAX_RETRIES: f64 = 3;

pub fn greet(user: User) -> String {
    return format!("Hello, {}! You are {} years old.", user.name, user.age);
}

pub async fn fetch_data(url: &str) -> String {
    let response = fetch(url).await;
    return response.text();
}

pub struct ApiClient {
    pub base_url: String,
}

impl ApiClient {
    pub fn new(&self, base_url: &str) {
        self.base_url = base_url;
    }

    pub async fn get(&self, path: &str) -> String {
        let full_url = format!("{}{}", self.base_url, path);
        tracing::info!("{}", full_url);
        return full_url;
    }
}

pub fn process_items(items: Vec<String>) -> f64 {
    let mut count = 0;
    for _item in items.iter() {
        if item.len() > 0 {
            count += 1;
        }
    }
    return count;
}

pub fn get_status(code: f64) -> String {
    match code {
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

pub fn safe_parse(input: &str) -> String {
    match (|| -> Result<(), Box<dyn std::error::Error>> {
        let result = serde_json::from_str(input).unwrap_or_default();
        return serde_json::to_string(&result).unwrap_or_default();
        Ok(())
    })() {
        Ok(()) => {}
        Err(e) => {
            tracing::error!("{}", e);
            return "{}";
        }
    }
}

// Utility: calculate distance
pub fn distance(x: f64, y: f64) -> f64 {
    return (x * x + y * y as f64).sqrt();
}

let numbers = vec![1, 2, 3];

let doubled = numbers.iter().map(|n| n * 2);

let total = numbers.reduce(|acc, n| acc + n, 0);