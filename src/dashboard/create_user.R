## This is AI-generated as it was mostly converting existing server-ui code and relocating it to a single file.

# When R is ran via RScript this command will execute and needs to communicate a little like a unix programmes / a bash script in terms of exit codes, where are the 0L/1L below.
EXIT_SUCCESS <- 0L
EXIT_FAILURE <- 1L
DIRECT_EXECUTION_FRAME_COUNT <- 0L


# Create a trusted account using matching passwords entered at the terminal.
create_user_cli <- function(arguments, prompt_password, create_user = create_auth_user) {
  usage <- "Usage: Rscript src/dashboard/create_user.R USERNAME"
  if (identical(arguments, "--help")) {
    cat(usage, "\nUsernames: 1-50 letters or numbers. Passwords: at least 12 characters.\n")
    return(EXIT_SUCCESS)
  }
  if (length(arguments) != 1) {
    message(usage)
    return(EXIT_FAILURE)
  }
  password <- prompt_password("Password: ")
  confirmation <- prompt_password("Confirm password: ")
  if (!identical(password, confirmation)) {
    message("Passwords do not match. No account was created.")
    return(EXIT_FAILURE)
  }
  if (!isTRUE(create_user(arguments[[1]], password))) {
    message("Username already exists. No account was changed.")
    return(EXIT_FAILURE)
  }
  cat("Account created. The user can now sign in.\n")
  EXIT_SUCCESS
}

# The below is equivalent to `if __name__ == "__main__":` - withold execution to direct invocation of this script
# Basically avoid running this outside of when we want this to be invoked
# - when tests run source(create_user.R) we want to prevent the code below running so we can manually invoke the function above
if (sys.nframe() == DIRECT_EXECUTION_FRAME_COUNT) {
  arguments <- commandArgs(trailingOnly = TRUE)
  prompt_password <- NULL
  if (length(arguments) == 1 && arguments != "--help") {
    script_file <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE))
    dashboard_dir <- dirname(normalizePath(script_file))
    source(file.path(dashboard_dir, "R", "db.R"))
    source(file.path(dashboard_dir, "R", "auth.R"))
    getpass <- reticulate::import("getpass")
    reticulate::import("warnings")$simplefilter("error", getpass$GetPassWarning)
    prompt_password <- getpass$getpass
  }
  quit(status = create_user_cli(arguments, prompt_password))
}
