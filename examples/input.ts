// Sample TypeScript file demonstrating key features

interface User {
  name: string;
  age: number;
  email?: string;
}

enum Status {
  Active,
  Inactive,
  // Pending status
  Pending,
}

type Config = {
  host: string;
  port: number;
  debug?: boolean;
};

export const MAX_RETRIES: number = 3;

export function greet(user: User): string {
  return `Hello, ${user.name}! You are ${user.age} years old.`;
}

export const fetchData = async (url: string): Promise<string> => {
  const response = await fetch(url);
  return response.text();
};

class ApiClient {
  baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async get(path: string): Promise<string> {
    const fullUrl = `${this.baseUrl}${path}`;
    console.log(fullUrl);
    return fullUrl;
  }
}

function processItems(items: string[]): number {
  let count = 0;
  for (const item of items) {
    if (item.length > 0) {
      count += 1;
    }
  }
  return count;
}

function getStatus(code: number): string {
  switch (code) {
    case 200:
      return "OK";
    case 404:
      return "Not Found";
    default:
      return "Unknown";
  }
}

function safeParse(input: string): string {
  try {
    const result = JSON.parse(input);
    return JSON.stringify(result);
  } catch (e) {
    console.error(e);
    return "{}";
  }
}

// Utility: calculate distance
function distance(x: number, y: number): number {
  return Math.sqrt(x * x + y * y);
}

const numbers = [1, 2, 3];
const doubled = numbers.map((n) => n * 2);
const total = numbers.reduce((acc, n) => acc + n, 0);
