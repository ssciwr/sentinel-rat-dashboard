AUTH_PACKAGES <- c("shinymanager", "scrypt")
CRAN_REPOSITORY <- "https://cran.r-project.org"

packages <- c(
  "shiny",
  AUTH_PACKAGES,
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
package_repositories <- getOption("repos", c(CRAN = CRAN_REPOSITORY))
package_repositories[package_repositories == "@CRAN@"] <- CRAN_REPOSITORY

install.packages(
  setdiff(packages, AUTH_PACKAGES),
  repos = package_repositories
)
install.packages(AUTH_PACKAGES, repos = CRAN_REPOSITORY)

