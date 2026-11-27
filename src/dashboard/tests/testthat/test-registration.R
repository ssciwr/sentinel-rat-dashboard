source(file.path("..", "..", "server", "settings_server.R"), local = TRUE)
source(file.path("..", "..", "ui", "settings.R"), local = TRUE)
NEW_REGISTRATION_USER <- "Rat12"
REGISTRATION_PASSWORD <- "sample-password"

# Next line is AI-generated cases.
INVALID_REGISTRATION_USERS <- c("", " ", "rat_12", "rat-12", "rat.12", "rat 12", " Rat12", "Rat12 ",
  "Rat12\n", "rat\u00e912", strrep("u", 51))
source(file.path("..", "..", "create_user.R"), local = TRUE)

make_registration_store <- function() {
  store <- make_auth_store(users)
  auth_functions <- new.env()
  sys.source(file.path("..", "..", "R", "auth.R"), envir = auth_functions)
  # Monkeypath these auth functions so we can track reuslts:
  auth_functions$create_db_session <- function() list(close = base::invisible)
  auth_functions$app_user_crud <- list(
    get_login = function(session, user) {
      account <- store$fetch(user)
      if (nrow(account) == 0) return(NULL)
      account
    },
    add = function(session, username, password) {
      store$rows <- rbind(store$rows, data.frame(
        app_user_id = max(store$rows$app_user_id) + 1L, user = username,
        password = password, is_active = TRUE
      ))
    }
  )
  store$create <- auth_functions$create_auth_user #

  store$server <- function(input, output, session) {
    auth <- register_auth_server(input, session, store$fetch)
    credentials <- auth$credentials
  }
  store
}

test_that("registration stores a password hash that verifies the submitted password", {
  store <- make_registration_store()
  created <- store$create(NEW_REGISTRATION_USER, REGISTRATION_PASSWORD)
  password_hash <- store$fetch(NEW_REGISTRATION_USER)$password
  expect_true(created)
  expect_true(scrypt::verifyPassword(password_hash, REGISTRATION_PASSWORD))
  expect_false(scrypt::verifyPassword(password_hash, "sample-password "))
})

test_that("short passwords or empty passwords both fail", {
  store <- make_registration_store()
  user <- strrep("u", 50)
  expect_error(store$create(user, ""))
  expect_error(store$create(user, "shortpw")) # 7 chars, under the 12 minimum
  expect_error(store$create(user, "samplepass1"))
  expect_identical(store$rows, users)
})

test_that("passwords of twelve characters or longer are accepted", {
  for (password in c("samplepass12", "samplepass123")) {
    store <- make_registration_store()
    user <- strrep("Rat12", 10)
    created <- store$create(user, password)
    expect_true(created)
    expect_identical(nrow(store$rows), 3L)
    expect_true(scrypt::verifyPassword(store$fetch(user)$password, password))
  }
})

# Usernames that use characters beyond A-Za-z0-9 will be rejected
test_that("usernames must just be strings and numbers", {
  store <- make_registration_store()
  for (user in INVALID_REGISTRATION_USERS) expect_error(store$create(user, REGISTRATION_PASSWORD))
  expect_identical(store$rows, users)
  expect_identical(store$fetch(NEW_REGISTRATION_USER)$user, character())
})

# Important for actual functionality
test_that("the settings menu offers login without public sign-up", {
  testServer(register_settings_server, {
    menu <- output$settings_menu$html
    expect_match(menu, 'id="settings_open".*Login')
    expect_false(grepl("register|Create account", menu))
    expect_false(grepl("Sign in/up", output$settings_button$html, fixed = TRUE))
    expect_match(output$settings_auth$html, 'id="settings_login-user_id"')
  })
})

test_that("old registration inputs cannot replace the login form", {
  testServer(register_settings_server, {
    session$setInputs(settings_register_open = 1)
    expect_match(output$settings_auth$html, 'id="settings_login-user_id"')
    expect_false(grepl("settings_create_account", output$settings_auth$html, fixed = TRUE))
    expect_false(can_manage_cameras())
  })
})

test_that("old registration submissions cannot create an account or sign in", {
  store <- make_registration_store()
  rlang::local_bindings(create_auth_user = store$create, .env = environment(register_auth_server))
  testServer(store$server, {
    session$setInputs(settings_register_open = 1)
    session$setInputs(settings_register_user = NEW_REGISTRATION_USER, settings_register_password = REGISTRATION_PASSWORD, settings_register_password_confirm = REGISTRATION_PASSWORD, settings_create_account = 1)
    expect_false(credentials$result)
    expect_identical(store$rows, users)
    expect_null(credentials$user_info)
  })
})

registration_password_prompt <- function(prompt) REGISTRATION_PASSWORD

test_that("the CLI creates an active account with a hashed password", {
  store <- make_registration_store()
  capture.output(status <- create_user_cli(NEW_REGISTRATION_USER, registration_password_prompt, store$create))
  account <- store$fetch(NEW_REGISTRATION_USER)
  expect_identical(status, 0L)
  expect_true(account$is_active)
  expect_true(scrypt::verifyPassword(account$password, REGISTRATION_PASSWORD))
})

test_that("accounts created by the CLI can log in", {
  store <- make_registration_store()
  capture.output(create_user_cli(NEW_REGISTRATION_USER, registration_password_prompt, store$create))
  testServer(store$server, {
    login_settings(session, NEW_REGISTRATION_USER, REGISTRATION_PASSWORD)
    expect_true(credentials$result)
    expect_identical(credentials$user_info$user, NEW_REGISTRATION_USER)
    expect_false("password" %in% names(credentials$user_info))
  })
})

test_that("the CLI leaves existing accounts unchanged", {
  store <- make_registration_store()
  store$create(NEW_REGISTRATION_USER, REGISTRATION_PASSWORD)
  before <- store$rows
  expect_message(status <- create_user_cli(NEW_REGISTRATION_USER, registration_password_prompt, store$create), "Username already exists")
  expect_identical(status, 1L)
  expect_identical(store$rows, before)
})

# AI-Generated
# Supply a different confirmation password to check that creation stops.
mismatched_password_prompt <- function(prompt) {
  if (prompt == "Password: ") REGISTRATION_PASSWORD else paste0(REGISTRATION_PASSWORD, " ")
}

test_that("the CLI requires matching passwords before creating an account", {
  store <- make_registration_store()
  expect_message(status <- create_user_cli(NEW_REGISTRATION_USER, mismatched_password_prompt, store$create), "Passwords do not match")
  expect_identical(status, 1L)
  expect_identical(store$rows, users)
})

test_that("the CLI rejects missing or extra arguments without creating accounts", {
  store <- make_registration_store()
  for (arguments in list(character(), c("Rat12", "Extra"))) {
    expect_message(status <- create_user_cli(arguments, registration_password_prompt, store$create), "Usage:")
    expect_identical(status, 1L)
    expect_identical(store$rows, users)
  }
})
