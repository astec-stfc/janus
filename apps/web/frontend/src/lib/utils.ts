import axios from "axios";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function subtractMean(data: number[]): number[] {
  if (data.length === 0) return data;
  const mean = data.reduce((acc, v) => acc + v, 0) / data.length;
  return data.map((v) => v - mean);
}

export function getCssVariable(name: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

export function getErrorMessage(error: unknown, fallback = "Unknown error"): string {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail;
  }
  return error instanceof Error ? error.message : fallback;
}
