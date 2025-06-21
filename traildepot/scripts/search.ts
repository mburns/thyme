import { addRoute, jsonHandler, parsePath } from "../trailbase.js";

/// Register a handler for the `/search` API route.
addRoute(
  "GET",
  "/search",
  jsonHandler(async (req) => {
    // Get the query params from the url, e.g. '/search?q=godfather&page=1&titles=true&persons=true&years=true'.
    const searchParams = parsePath(req.uri).query;
    const searchQuery = searchParams.get("q") ?? "";
    const page = parseInt(searchParams.get("page") ?? "1");
    const limit = parseInt(searchParams.get("limit") ?? "20");
    const offset = (page - 1) * limit;

    // Filter options
    const includeTitles = searchParams.get("titles") !== "false";
    const includePersons = searchParams.get("persons") !== "false";
    const includeYears = searchParams.get("years") !== "false";

    console.log(
      `[SEARCH] Handler called with query='${searchQuery}', page=${page}, limit=${limit}, offset=${offset}, filters: titles=${includeTitles}, persons=${includePersons}, years=${includeYears}`,
    );

    if (!searchQuery.trim()) {
      return {
        results: [],
        totalPages: 0,
        currentPage: page,
        totalResults: 0,
        query: searchQuery,
      };
    }

    try {
      // biome-ignore lint/suspicious/noExplicitAny: TODO
      const allResults: any[] = [];
      let totalResults = 0;

      // Search titles
      if (includeTitles) {
        const titlesUrl = `/api/records/v1/titles?filter[primaryTitle][$like]=%${searchQuery}%&limit=${limit}&offset=${offset}`;
        console.log(`[SEARCH] Searching titles: ${titlesUrl}`);

        const titlesResponse = await fetch(`http://localhost:4000${titlesUrl}`);
        const titlesData = (await titlesResponse.json()) as { records?: any[] };

        // biome-ignore lint/suspicious/noExplicitAny: TODO
        const titleResults = (titlesData.records || []).map((row: any) => ({
          id: row.id,
          type: "title",
          tconst: row.tconst,
          titleType: row.titleType || null,
          primaryTitle: row.primaryTitle || "Unknown Title",
          primaryName: row.primaryTitle || "Unknown Title",
          originalTitle: row.originalTitle || null,
          startYear: row.startYear || null,
          endYear: row.endYear || null,
          genres: row.genres || null,
          averageRating: null,
          numVotes: null,
        }));

        allResults.push(...titleResults);
        totalResults += titleResults.length;
      }

      // Search persons
      if (includePersons) {
        const personsUrl = `/api/records/v1/persons?filter[primaryName][$like]=%${searchQuery}%&limit=${limit}&offset=${offset}`;
        console.log(`[SEARCH] Searching persons: ${personsUrl}`);

        const personsResponse = await fetch(
          `http://localhost:4000${personsUrl}`,
        );
        const personsData = (await personsResponse.json()) as {
          records?: any[];
        };

        // biome-ignore lint/suspicious/noExplicitAny: TODO
        const personResults = (personsData.records || []).map((row: any) => ({
          id: row.id,
          type: "person",
          nconst: row.nconst,
          primaryName: row.primaryName || "Unknown Person",
          primaryTitle: row.primaryName || "Unknown Person",
          birthYear: row.birthYear || null,
          deathYear: row.deathYear || null,
          primaryProfession: row.primaryProfession || null,
          // Person-specific fields
          titleType: null,
          originalTitle: null,
          startYear: row.birthYear || null,
          endYear: row.deathYear || null,
          genres: row.primaryProfession || null,
          averageRating: null,
          numVotes: null,
        }));

        allResults.push(...personResults);
        totalResults += personResults.length;
      }

      // Search by year (titles with specific year)
      if (includeYears && /^\d{4}$/.test(searchQuery)) {
        const yearUrl = `/api/records/v1/titles?filter[startYear][$eq]=${searchQuery}&limit=${limit}&offset=${offset}`;
        console.log(`[SEARCH] Searching by year: ${yearUrl}`);

        const yearResponse = await fetch(`http://localhost:4000${yearUrl}`);
        const yearData = (await yearResponse.json()) as { records?: any[] };

        // biome-ignore lint/suspicious/noExplicitAny: TODO
        const yearResults = (yearData.records || []).map((row: any) => ({
          id: row.id,
          type: "title",
          tconst: row.tconst,
          titleType: row.titleType || null,
          primaryTitle: row.primaryTitle || "Unknown Title",
          primaryName: row.primaryTitle || "Unknown Title",
          originalTitle: row.originalTitle || null,
          startYear: row.startYear || null,
          endYear: row.endYear || null,
          genres: row.genres || null,
          averageRating: null,
          numVotes: null,
        }));

        allResults.push(...yearResults);
        totalResults += yearResults.length;
      }

      // Sort results by relevance (titles first, then persons)
      // biome-ignore lint/suspicious/noExplicitAny: TODO
      allResults.sort((a: any, b: any) => {
        if (a.type === "title" && b.type === "person") return -1;
        if (a.type === "person" && b.type === "title") return 1;
        return 0;
      });

      const totalPages = Math.ceil(totalResults / limit);

      console.log(
        `[SEARCH] Returning ${allResults.length} total results (${totalResults} total found)`,
      );
      return {
        results: allResults,
        totalPages,
        currentPage: page,
        totalResults,
        query: searchQuery,
        filters: {
          titles: includeTitles,
          persons: includePersons,
          years: includeYears,
        },
      };
    } catch (error) {
      console.error("Search error:", error);
      return {
        results: [],
        totalPages: 0,
        currentPage: page,
        totalResults: 0,
        query: searchQuery,
        error: "Search failed",
      };
    }
  }),
);
