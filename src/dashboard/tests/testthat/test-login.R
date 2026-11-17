# Basic login authentication (no camera dashboard content yet)
login_server <- function(input, output, session) {
  credentials <- register_auth_server(input, session)$credentials
}

default_login <- list(user = "first-user", password = "test-password", is_active = TRUE, stored_password = users$password[1])
rejected_logins <- list(
  list(user = "missing"),
  list(user = "first-user "),
  list(user = "' OR 1=1 --"),
  list(password = ""),
  list(password = "test-password "),
  list(password = strrep("x", 4096)),
  list(is_active = FALSE),
  list(stored_password = NA_character_),
  list(stored_password = scrypt::hashPassword("updated-password"))
)
login_notice <- new.env()

record_login_notice <- function(ui, ...) {
  login_notice$text <- as.character(ui)
}

# Confirm relogin works
test_that("active logins retain identity without exposing password hashes", {
  for (user in users$user) testServer(login_server, {
    expect_false(credentials$result)
    login_settings(session, user)
    html <- as.character(shinymanager::auth_ui("settings_login"))
    expect_match(html, 'type="password"')
    expect_true(credentials$result)
    expect_identical(credentials$user_info$app_user_id, users$app_user_id[users$user == user])
    expect_identical(credentials$user_info$user, user)
    expect_false("password" %in% names(credentials$user_info) || grepl(users$password[1], html, fixed = TRUE))
  })
})

# only valid passwords accepted
test_that("invalid credentials and unavailable accounts cannot authenticate", {
  for (rejected_login in rejected_logins) {
    login <- modifyList(default_login, rejected_login)
    store <- make_auth_store(transform(users, is_active = login$is_active, password = login$stored_password))
    rlang::local_bindings(fetch_auth_user = store$fetch, .env = environment(register_auth_server))
    testServer(login_server, {
      login_settings(session, login$user, login$password)
      expect_false(credentials$result)
      expect_null(credentials$user_info)
      expect_null(credentials$user)
    })
  }
})

# Password (+ hashed password) updates persist  (ready) for the next login
test_that("logout clears identity and the next login reads the current password", {
  store <- make_auth_store()
  rlang::local_bindings(fetch_auth_user = store$fetch, .env = environment(register_auth_server))
  testServer(login_server, {
    login_settings(session)
    session$setInputs(settings_logout = 1)
    expect_false(credentials$result)
    expect_null(credentials$user_info)
    store$rows$password <- scrypt::hashPassword("updated-password")
    login_settings(session, "second-user", "updated-password", button = 2L)
    expect_true(credentials$result)
    expect_identical(credentials$user_info$app_user_id, 2L)
    expect_false("password" %in% names(credentials$user_info))
  })
})

test_that("a wrong password does not work", {
  store <- make_auth_store()
  rlang::local_bindings(fetch_auth_user = store$fetch, showNotification = record_login_notice, .env = environment(register_auth_server))
  for (database_failed in c(FALSE, TRUE)) testServer(login_server, {
    store$fail <- database_failed
    username <- if (database_failed) "first-user" else c("first-user", "second-user")
    expect_message(login_settings(session, user = username), "Settings login could not be verified")
    expect_false(credentials$result)
    expect_null(credentials$user_info)
    expect_identical(login_notice$text, "Login could not be checked. Please try again later.")
  })
})
