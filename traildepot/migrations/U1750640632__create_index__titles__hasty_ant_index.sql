CREATE INDEX "_titles__hasty_ant_index" ON 'titles' ('tconst' ASC, 'primaryTitle' DESC);
CREATE INDEX "_ratings__gnarly_ant_index" ON 'ratings' ('title_id' ASC, 'averageRating' DESC);
CREATE INDEX "_persons__fresh_badger_index" ON 'persons' ('nconst' ASC, 'primaryName' DESC);