# Handle authentication

register_auth_server <- function(input, session, fetch_user = fetch_auth_user) {
  failed_login <- list(result = FALSE, expired = FALSE, authorized = FALSE, user_info = NULL)

  check_account_credentials <- function(user, password) {
    tryCatch({
      account <- fetch_user(user)
      if (nrow(account) != 1 || !isTRUE(account$is_active) || is.na(account$password)) {
        return(failed_login)
      }
      account$is_hashed_password <- TRUE
      shinymanager::check_credentials(account)(user, password)
    }, error = function(error) {
      message("Settings login could not be verified.")
      showNotification("Login could not be checked. Please try again later.", type = "error")
      failed_login
    })
  }
  credentials <- callModule(shinymanager::auth_server, "settings_login", check_credentials = check_account_credentials)

  can_manage_cameras <- function() {
    if (!isTRUE(credentials$result)) return(FALSE)
    tryCatch({
      account <- fetch_user(credentials$user)
      nrow(account) == 1 && isTRUE(account$is_active) &&
        identical(account$app_user_id, credentials$user_info$app_user_id)
    }, error = function(error) {
      message("User access could not be checked.")
      FALSE
    })
  }

  observeEvent(input$settings_logout, {
    credentials$result <- FALSE
    credentials$user <- NULL
    credentials$user_info <- NULL
    updateTextInput(session, "settings_login-user_pwd", value = "")
  })

  list(credentials = credentials, can_manage_cameras = can_manage_cameras)
}
