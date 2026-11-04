packages <- c(
  "shiny",
  "shinymanager",
  "scrypt",
  "RPostgres",
  "DBI",
  "dplyr",
  "ggplot2",
  "pool",
  "testthat",
  "covr",
  "xml2",
  "reticulate"
)
install.packages(
  setdiff(packages, c("shinymanager", "scrypt")),
  repos = "https://packagemanager.posit.co/cran/latest/bin/linux/jammy-x86_64/4.3"
)
install.packages(c("shinymanager", "scrypt"), repos = "https://cran.r-project.org")

