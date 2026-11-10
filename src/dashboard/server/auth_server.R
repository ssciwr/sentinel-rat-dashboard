# Handle authentication

register_auth_server <- function(input, session, fetch_user = fetch_auth_user, create_user = create_auth_user) {
  registration <- reactiveVal(FALSE)
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

  observeEvent(input$settings_register_open, {
    req(!isTRUE(credentials$result))
    registration(TRUE)
  })

  observeEvent(input$settings_open, {
    registration(FALSE)
  })

  observeEvent(input$settings_login_open, {
    updateTextInput(session, "settings_register_password", value = "")
    updateTextInput(session, "settings_register_password_confirm", value = "")
    registration(FALSE)
  })

  observeEvent(input$settings_create_account, {
    req(!isTRUE(credentials$result), registration())
    tryCatch({
      user <- input$settings_register_user
      password <- input$settings_register_password
      if (!is.character(user) || length(user) != 1 || is.na(user) || !nzchar(trimws(user)) || nchar(trimws(user)) > 50) {
        showNotification("Enter a username of 1 to 50 characters.", type = "error")
        return()
      }
      user <- trimws(user)
      if (!is.character(password) || length(password) != 1 || is.na(password) || nchar(password) < 8) {
        showNotification("Use at least 8 characters for your password.", type = "error")
        return()
      }
      if (!identical(password, input$settings_register_password_confirm)) {
        showNotification("Passwords do not match.", type = "error")
        return()
      }
      if (!isTRUE(create_user(user, password))) {
        showNotification("That username is already registered. Please log in.", type = "warning")
        return()
      }
      updateTextInput(session, "settings_register_password", value = "")
      updateTextInput(session, "settings_register_password_confirm", value = "")
      registration(FALSE)
      account_login <- check_account_credentials(user, password)
      if (!isTRUE(account_login$result)) {
        showNotification("Account created, but sign-in could not be completed. Please log in.", type = "error")
        return()
      }
      credentials$user <- user
      credentials$user_info <- account_login$user_info
      credentials$result <- TRUE
      session$sendCustomMessage("account_registered", NULL)
      showNotification("Account created. You are now signed in.", type = "message")
    }, error = function(error) {
      message("Account registration could not be completed.")
      showNotification("Account could not be created. Please try again later.", type = "error")
    })
  })

  list(credentials = credentials, can_manage_cameras = can_manage_cameras, registration = registration)
}
