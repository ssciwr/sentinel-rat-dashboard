source(file.path("..", "..", "server", "settings_server.R"), local = TRUE)
source(file.path("..", "..", "ui", "settings.R"), local = TRUE)
NEW_REGISTRATION_USER <- "Rat12"
REGISTRATION_PASSWORD <- "sample-password"

# Next line is AI-generated cases.
INVALID_REGISTRATION_USERS <- c("", " ", "rat_12", "rat-12", "rat.12", "rat 12", " Rat12", "Rat12 ",
  "Rat12\n", "rat\u00e912", strrep("u", 51))
registration_notice <- new.env()

# Capture response from ui for testing (rather than opening a browser window)
record_registration_notice <- function(ui, ...) {
  registration_notice$text <- as.character(ui)
}

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
    auth <- register_auth_server(input, session, store$fetch, store$create)
    credentials <- auth$credentials
    registration <- auth$registration
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
test_that("the settings dialog switches between login and a basic registration form", {
  testServer(register_settings_server, {
    session$setInputs(settings_register_open = 1)
    registration_html <- output$settings_auth$html
    session$setInputs(settings_login_open = 1)
    expect_match(registration_html, 'type="password"')
    expect_match(registration_html, 'id="settings_create_account"')
    expect_match(output$settings_auth$html, 'id="settings_login-user_id"')
  })
})

test_that("the settings menu opens registration directly and Login resets the form", {
  testServer(register_settings_server, {
    menu <- output$settings_menu$html
    session$setInputs(settings_register_open = 1)
    registration_html <- output$settings_auth$html
    session$setInputs(settings_open = 1)
    expect_match(menu, 'id="settings_register_open".*Create account')
    expect_match(registration_html, 'id="settings_create_account"')
    expect_match(output$settings_auth$html, 'id="settings_login-user_id"')
  })
})


test_that("invalid usernames cannot register", {
  store <- make_registration_store()
  rlang::local_bindings(showNotification = record_registration_notice, .env = environment(register_auth_server))
  for (user in INVALID_REGISTRATION_USERS) testServer(store$server, {
    session$setInputs(settings_register_open = 1)
    session$setInputs(settings_register_user = user, settings_register_password = REGISTRATION_PASSWORD, settings_register_password_confirm = REGISTRATION_PASSWORD, settings_create_account = 1)
    expect_false(credentials$result)
    expect_identical(store$rows, users)
    expect_identical(registration_notice$text, "Use 1 to 50 letters (a-z, A-Z) or numbers (0-9) for your username.")
  })
})

test_that("Error is shown (kept generic) if an account cannot be created (typically, being an attempted duplicate registration of an existing one)", {
  store <- make_registration_store()
  rlang::local_bindings(showNotification = record_registration_notice, .env = environment(register_auth_server))
  store$fail <- TRUE
  testServer(store$server, {
    session$setInputs(settings_register_open = 1, settings_register_user = NEW_REGISTRATION_USER, settings_register_password = REGISTRATION_PASSWORD, settings_register_password_confirm = REGISTRATION_PASSWORD)
    expect_message(session$setInputs(settings_create_account = 1), "Account registration could not be completed")
    expect_identical(registration_notice$text, "Account could not be created. Please try again later.")
    expect_identical(store$rows, users)
  })
})

test_that("User must submit matching passwords during registration", {
  store <- make_registration_store()
  rlang::local_bindings(showNotification = record_registration_notice, .env = environment(register_auth_server))
  for (confirmation in c("", "sample-password ")) testServer(store$server, {
    session$setInputs(settings_register_open = 1, settings_register_user = NEW_REGISTRATION_USER, settings_register_password = REGISTRATION_PASSWORD, settings_register_password_confirm = confirmation)
    session$setInputs(settings_create_account = 1)
    expect_false(credentials$result)
    expect_identical(store$rows, users)
    expect_identical(registration_notice$text, "Passwords do not match.")
  })
})
