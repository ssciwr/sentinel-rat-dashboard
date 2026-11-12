source("../../server/settings_server.R", local = TRUE)
source("../../ui/settings.R", local = TRUE)
registration_notice <- new.env()

# Capture response from ui for testing (rather than opening a browser window)
record_registration_notice <- function(ui, ...) {
  registration_notice$text <- as.character(ui)
}

make_registration_store <- function() {
  store <- make_auth_store(users)
  auth_functions <- new.env()
  sys.source("../../R/auth.R", envir = auth_functions)
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
  created <- store$create("new-user", "sample-password")
  password_hash <- store$fetch("new-user")$password
  expect_true(created)
  expect_true(scrypt::verifyPassword(password_hash, "sample-password"))
  expect_false(scrypt::verifyPassword(password_hash, "sample-password "))
})

test_that("short passwords or empty passwords both fail", {
  store <- make_registration_store()
  user <- strrep("u", 50)
  expect_error(store$create(user, ""))
  expect_error(store$create(user, "shortpw")) # 7 chars, under the 8 minimum
  expect_identical(store$rows, users)
})

test_that("passwords of eight characters or longer are accepted", {
  for (password in c("samplepw", "samplepass12")) {
    store <- make_registration_store()
    user <- strrep("u", 50)
    created <- store$create(user, password)
    expect_true(created)
    expect_identical(nrow(store$rows), 3L)
    expect_true(scrypt::verifyPassword(store$fetch(user)$password, password))
  }
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


test_that("Empty usernames are disallowed", {
  store <- make_registration_store()
  for (user in c(" ", "")) testServer(store$server, {
    session$setInputs(settings_register_open = 1)
    session$setInputs(settings_register_user = user, settings_register_password = "sample-password", settings_register_password_confirm = "sample-password", settings_create_account = 1)
    expect_true(registration())
    expect_false(credentials$result)
    expect_identical(store$rows, users)
  })
})

test_that("Error is shown (kept generic) if an account cannot be created (typically, being an attempted duplicate registration of an existing one)", {
  store <- make_registration_store()
  rlang::local_bindings(showNotification = record_registration_notice, .env = environment(register_auth_server))
  store$fail <- TRUE
  testServer(store$server, {
    session$setInputs(settings_register_open = 1, settings_register_user = "new-user", settings_register_password = "sample-password", settings_register_password_confirm = "sample-password")
    expect_message(session$setInputs(settings_create_account = 1), "Account registration could not be completed")
    expect_identical(registration_notice$text, "Account could not be created. Please try again later.")
    expect_identical(store$rows, users)
  })
})

test_that("User must submit matching passwords during registration", {
  store <- make_registration_store()
  rlang::local_bindings(showNotification = record_registration_notice, .env = environment(register_auth_server))
  for (confirmation in c("", "sample-password ")) testServer(store$server, {
    session$setInputs(settings_register_open = 1, settings_register_user = "new-user", settings_register_password = "sample-password", settings_register_password_confirm = confirmation)
    session$setInputs(settings_create_account = 1)
    expect_false(credentials$result)
    expect_identical(store$rows, users)
    expect_identical(registration_notice$text, "Passwords do not match.")
  })
})
