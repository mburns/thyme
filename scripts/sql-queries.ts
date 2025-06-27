import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "fs-extra";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SQL_DIR = path.join(__dirname, "..", "sql");

export async function loadSql(filename: string): Promise<string> {
  const sqlPath = path.join(SQL_DIR, filename);
  if (!(await fs.pathExists(sqlPath))) {
    throw new Error(`SQL file not found: ${sqlPath}`);
  }

  return (await fs.readFile(sqlPath, "utf-8")).trim();
}

export class SQLQueries {
  private sqlDir: string;

  constructor(sqlDir?: string) {
    this.sqlDir = sqlDir || SQL_DIR;
  }

  async load(filename: string): Promise<string> {
    const sqlPath = path.join(this.sqlDir, filename);
    return (await fs.readFile(sqlPath, "utf-8")).trim();
  }

  async getTempTables(): Promise<string> {
    return this.load("temp_tables.sql");
  }

  async getImportTitles(): Promise<string> {
    return this.load("import_titles.sql");
  }

  async getImportPersons(): Promise<string> {
    return this.load("import_persons.sql");
  }

  async getImportRatings(): Promise<string> {
    return this.load("import_ratings.sql");
  }

  async getImportEpisodes(): Promise<string> {
    return this.load("import_episodes.sql");
  }

  async getImportPrincipals(): Promise<string> {
    return this.load("import_principals.sql");
  }

  async getImportCrewDirectors(): Promise<string> {
    return this.load("import_crew.sql");
  }

  async getImportCrewWriters(): Promise<string> {
    return this.load("import_crew_writers.sql");
  }
}

// Global instance for easy access
export const queries = new SQLQueries();
