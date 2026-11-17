library(shiny)
source(file.path("..", "..", "server", "auth_server.R"), local = TRUE)
PRIMARY_LOGIN_USER <- "first-user"
users <- data.frame(app_user_id = 1:2, user = c(PRIMARY_LOGIN_USER, "second-user"), password = scrypt::hashPassword("test-password"), is_active = TRUE)

# AI generated and checked authentication fixtures for auth tests

# Provide mutable database users for permission and password-change tests.
make_auth_store <- function(rows = users) {
  store <- new.env()
  store$rows <- rows
  # Return the current account or simulate an unavailable database.
  store$fetch <- function(user) {
    if (isTRUE(store$fail)) stop("private-database-detail", call. = FALSE)
    stopifnot(is.character(user), length(user) == 1, !is.na(user))
    store$rows[store$rows$user == user, , drop = FALSE]
  }
  store
}
fetch_auth_user <- make_auth_store()$fetch

# Submit credentials through the authentication library's actual inputs.
login_settings <- function(session, user = PRIMARY_LOGIN_USER, password = "test-password", button = 1L) {
  session$flushReact()
  session$setInputs(`settings_login-user_id` = user, `settings_login-user_pwd` = password, `settings_login-go_auth` = button)
}
