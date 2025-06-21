import type { TimelineEra, TimelineEvent, TimelineResponse } from "../../types/index.js";
import { addRoute, jsonHandler, parsePath } from "../trailbase.js";

/// Register a handler for the `/timeline` API route.
addRoute(
  "GET",
  "/timeline",
  jsonHandler(async (req): Promise<TimelineResponse> => {
    // Get the query params from the url, e.g. '/timeline?startYear=1900&limit=100&includeTitles=true&includePersons=true'.
    const searchParams = parsePath(req.uri).query;
    const startYear = parseInt(searchParams.get("startYear") ?? "1900");
    const limit = parseInt(searchParams.get("limit") ?? "100");
    const includeTitles = searchParams.get("includeTitles") !== "false";
    const includePersons = searchParams.get("includePersons") !== "false";

    console.log(
      `[TIMELINE] Handler called with startYear=${startYear}, limit=${limit}, filters: titles=${includeTitles}, persons=${includePersons}`,
    );

    try {
      const timelineEvents: TimelineEvent[] = [];
      const timelineEras: TimelineEra[] = [
        {
          start_date: { year: 1440 },
          end_date: { year: 1800 },
          text: {
            headline: "Printing Press Era",
            text: "The invention and spread of the printing press, enabling mass communication"
          }
        },
        {
          start_date: { year: 1844 },
          end_date: { year: 1900 },
          text: {
            headline: "Telegraph Era",
            text: "The rise of electrical communication with the telegraph"
          }
        },
        {
          start_date: { year: 1877 },
          end_date: { year: 1927 },
          text: {
            headline: "Recorded Sound Era",
            text: "From Edison's phonograph to the transition to sound films"
          }
        },
        {
          start_date: { year: 1900 },
          end_date: { year: 1927 },
          text: {
            headline: "Silent Film Era",
            text: "The golden age of silent cinema and early film pioneers"
          }
        },
        {
          start_date: { year: 1927 },
          end_date: { year: 1934 },
          text: {
            headline: "Talkies Revolution",
            text: "The transition from silent films to sound with 'The Jazz Singer'"
          }
        },
        {
          start_date: { year: 1935 },
          end_date: { year: 1950 },
          text: {
            headline: "Color Film Era",
            text: "The transition from black and white to color filmmaking"
          }
        },
        {
          start_date: { year: 1951 },
          end_date: { year: 1969 },
          text: {
            headline: "Golden Age of Hollywood",
            text: "The peak of studio system and classic cinema"
          }
        },
        {
          start_date: { year: 1970 },
          end_date: { year: 1989 },
          text: {
            headline: "New Hollywood Era",
            text: "The rise of independent filmmaking and blockbuster cinema"
          }
        },
        {
          start_date: { year: 1990 },
          end_date: { year: 1996 },
          text: {
            headline: "Digital Revolution Begins",
            text: "Early CGI and digital filmmaking techniques"
          }
        },
        {
          start_date: { year: 1997 },
          end_date: { year: 2007 },
          text: {
            headline: "Netflix Era",
            text: "The rise of streaming and digital distribution"
          }
        },
        {
          start_date: { year: 2008 },
          end_date: { year: 2019 },
          text: {
            headline: "Streaming Boom",
            text: "The explosion of streaming platforms and content"
          }
        },
        {
          start_date: { year: 2020 },
          end_date: { year: 2024 },
          text: {
            headline: "Pandemic & AI Era",
            text: "COVID-19 impact on cinema and the rise of AI in filmmaking"
          }
        }
      ];

      // Fetch titles with release dates
      if (includeTitles) {
        const titlesUrl = `/api/records/v1/v_title_details?filter[startYear][$ne]=null&order=startYear&limit=${limit}`;
        // console.log(`[TIMELINE] Fetching titles: ${titlesUrl}`);

        const titlesResponse = await fetch(`http://localhost:4000${titlesUrl}`);
        const titlesData = (await titlesResponse.json()) as { records?: any[] };

        // biome-ignore lint/suspicious/noExplicitAny: TODO
        const titleEvents = (titlesData.records || []).map((title: any) => {
          if (!title.startYear || !title.primaryTitle) return null;

          return {
            start_date: {
              year: title.startYear,
              month: 1,
              day: 1,
            },
            text: {
              headline: title.primaryTitle,
              text: `<p><strong>Type:</strong> ${title.titleType || 'Unknown'}</p>
                     <p><strong>Runtime:</strong> ${title.runtimeMinutes || 'Unknown'} minutes</p>
                     <p><strong>Genres:</strong> ${title.genres || 'Unknown'}</p>
                     ${title.averageRating ? `<p><strong>Rating:</strong> ${title.averageRating.toFixed(1)}/10 (${title.numVotes?.toLocaleString() || 0} votes)</p>` : ''}`,
            },
            media: {
              url: title.posterUrl || '',
              caption: title.originalTitle !== title.primaryTitle ? `Original title: ${title.originalTitle}` : '',
            },
            group: 'Movies',
            background: {
              color: '#2c3e50',
            },
            unique_id: `title_${title.id}`,
          } as TimelineEvent;
        }).filter((event): event is TimelineEvent => event !== null);

        timelineEvents.push(...titleEvents);
        // console.log(`[TIMELINE] Added ${titleEvents.length} title events`);
      }

      // Fetch persons with birth/death dates
      if (includePersons) {
        const personsUrl = `/api/records/v1/persons?filter[birthYear][$ne]=null&order=birthYear&limit=${Math.floor(limit / 2)}`;
        // console.log(`[TIMELINE] Fetching persons: ${personsUrl}`);

        const personsResponse = await fetch(`http://localhost:4000${personsUrl}`);
        const personsData = (await personsResponse.json()) as { records?: any[] };

        // biome-ignore lint/suspicious/noExplicitAny: TODO
        const personEvents = (personsData.records || []).map((person: any) => {
          if (!person.birthYear || !person.primaryName) return null;

          const profession = person.primaryProfession ? person.primaryProfession.split(',')[0].trim() : 'Unknown';

          return {
            start_date: {
              year: person.birthYear,
              month: person.birthMonth || 1,
              day: person.birthDay || 1,
            },
            end_date: person.deathYear ? {
              year: person.deathYear,
              month: person.deathMonth || 1,
              day: person.deathDay || 1,
            } : undefined,
            text: {
              headline: person.deathYear ? `${person.primaryName} (${person.birthYear}-${person.deathYear})` : `${person.primaryName} (Born ${person.birthYear})`,
              text: `<p><strong>Birth:</strong> ${person.birthYear}${person.birthMonth ? `-${person.birthMonth}` : ''}${person.birthDay ? `-${person.birthDay}` : ''}</p>
                     ${person.deathYear ? `<p><strong>Death:</strong> ${person.deathYear}${person.deathMonth ? `-${person.deathMonth}` : ''}${person.deathDay ? `-${person.deathDay}` : ''}</p>
                     <p><strong>Age:</strong> ${person.deathYear - person.birthYear} years</p>` : ''}
                     <p><strong>Profession:</strong> ${profession}</p>`,
            },
            group: profession,
            background: {
              color: person.deathYear ? '#8e44ad' : '#e74c3c',
            },
            unique_id: `person_${person.id}`,
          } as TimelineEvent;
        }).filter((event): event is TimelineEvent => event !== null);

        timelineEvents.push(...personEvents);
        // console.log(`[TIMELINE] Added ${personEvents.length} person events`);
      }

      // Sort events by date
      timelineEvents.sort((a, b) => {
        const dateA = new Date(a.start_date.year, (a.start_date.month || 1) - 1, a.start_date.day || 1);
        const dateB = new Date(b.start_date.year, (b.start_date.month || 1) - 1, b.start_date.day || 1);
        return dateA.getTime() - dateB.getTime();
      });

      // console.log(`[TIMELINE] Returning ${timelineEvents.length} total timeline events with ${timelineEras.length} eras`);
      return {
        events: timelineEvents,
        eras: timelineEras,
        totalEvents: timelineEvents.length,
        startYear,
        filters: {
          includeTitles,
          includePersons,
        },
      };
    } catch (error) {
      console.error("[TIMELINE] Timeline error:", error);
      return {
        events: [],
        eras: [],
        totalEvents: 0,
        startYear,
        filters: {
          includeTitles,
          includePersons,
        },
        error: "Timeline data fetch failed",
      };
    }
  }),
);
