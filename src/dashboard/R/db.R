library(DBI)
library(RPostgres)

fetch_analyses <- function() {
  con <- dbConnect(
    RPostgres::Postgres(),
    dbname = Sys.getenv("POSTGRES_DB", "sentinel_db"),
    host = Sys.getenv("POSTGRES_HOST", "db"),
    port = as.integer(Sys.getenv("POSTGRES_PORT", "5432")),
    user = Sys.getenv("POSTGRES_USER", "sentinel_user"),
    password = Sys.getenv("POSTGRES_PASSWORD", "sentinel_pass")
  )

  res <- dbGetQuery(
    con,
    "
    SELECT *
    FROM daily_analysis_result
    ORDER BY start_time DESC
    "
  )

  dbDisconnect(con)
  return(res)
}
