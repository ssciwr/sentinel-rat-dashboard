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
package_repositories <- getOption("repos", c(CRAN = "https://cran.r-project.org"))
package_repositories[package_repositories == "@CRAN@"] <- "https://cran.r-project.org"

install.packages(
  setdiff(packages, c("shinymanager", "scrypt")),
  repos = package_repositories
)
install.packages(c("shinymanager", "scrypt"), repos = "https://cran.r-project.org")

