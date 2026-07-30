library(DBI)
library(RPostgres)

source("R/db.R")

con <- dbConnect(
  RPostgres::Postgres(),
  dbname = Sys.getenv("POSTGRES_DB", "sentinel_db"),
  host = Sys.getenv("POSTGRES_HOST", "db"),
  port = as.integer(Sys.getenv("POSTGRES_PORT", "5432")),
  user = Sys.getenv("POSTGRES_USER", "sentinel_user"),
  password = Sys.getenv("POSTGRES_PASSWORD", "sentinel_pass")
)

dbListTables(con)
