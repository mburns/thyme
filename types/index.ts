// Common type definitions for the Thyme project

export interface Title {
  id: string;
  title: string;
  type: "movie" | "tvSeries" | "tvEpisode" | "short" | "video" | "videoGame";
  startYear?: number;
  endYear?: number;
  runtimeMinutes?: number;
  genres?: string[];
  averageRating?: number;
  numVotes?: number;
}

export interface Person {
  id: string;
  name: string;
  birthYear?: number;
  deathYear?: number;
  primaryProfession?: string[];
  knownForTitles?: string[];
}

export interface SearchResult {
  type: "title" | "person";
  id: string;
  title?: string;
  name?: string;
  year?: number;
  rating?: number;
  genres?: string[];
}

export interface SearchFilters {
  type?: "movie" | "tvSeries" | "person";
  year?: number;
  minRating?: number;
  genres?: string[];
}

export interface DatabaseConfig {
  path: string;
  readonly?: boolean;
}

export interface SearchOptions {
  query: string;
  filters?: SearchFilters;
  limit?: number;
  offset?: number;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface SearchResponse extends ApiResponse<SearchResult[]> {
  total?: number;
  page?: number;
  limit?: number;
}

// Error types
export class ThymeError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500,
  ) {
    super(message);
    this.name = "ThymeError";
  }
}

export class DatabaseError extends ThymeError {
  constructor(message: string) {
    super(message, "DATABASE_ERROR", 500);
    this.name = "DatabaseError";
  }
}

export class ValidationError extends ThymeError {
  constructor(message: string) {
    super(message, "VALIDATION_ERROR", 400);
    this.name = "ValidationError";
  }
}

export class NotFoundError extends ThymeError {
  constructor(resource: string) {
    super(`${resource} not found`, "NOT_FOUND", 404);
    this.name = "NotFoundError";
  }
}

// Timeline Types
export interface TimelineDate {
  year: number;
  month?: number;
  day?: number;
}

export interface TimelineText {
  headline: string;
  text: string;
}

export interface TimelineMedia {
  url: string;
  caption?: string;
}

export interface TimelineBackground {
  color?: string;
}

export interface TimelineEvent {
  start_date: TimelineDate;
  end_date?: TimelineDate;
  text: TimelineText;
  media?: TimelineMedia;
  group: string;
  background?: TimelineBackground;
  unique_id: string;
}

export interface TimelineEra {
  start_date: TimelineDate;
  end_date: TimelineDate;
  text: TimelineText;
}

export interface TimelineResponse {
  events: TimelineEvent[];
  eras?: TimelineEra[];
  totalEvents: number;
  startYear: number;
  filters: {
    includeTitles: boolean;
    includePersons: boolean;
  };
  error?: string;
}
