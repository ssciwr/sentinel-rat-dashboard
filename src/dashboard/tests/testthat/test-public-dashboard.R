# Build fake app for these sign in / sign out tests
public_app <- new.env(parent = environment())
public_app$source <- function(file, local = TRUE) {
  if (file != "R/db.R") sys.source(file.path("../..", file), envir = public_app)
}
sys.source("../../app.R", envir = public_app)
public_app$fetch_auth_user <- make_auth_store()$fetch

public_app$create_db_session <- function() list(close = base::invisible) # remove the real DB for this test

# Monkey patch/mock soem fake data
public_app$fetch_detections <- function(session) {
  data.frame(species = "Rattus rattus", confidence = 0.876)
}

test_that("Smoke test: Detectiosn can be seen (from the mocked fetch_detectiosn above) by a logged out user", {
  testServer(public_app$server, {
    detections_html <- output$results
    expect_match(detections_html, "Rattus rattus")
    expect_match(detections_html, "0.88")
    # And that was while the user was not signed in
    expect_false(auth$credentials$result)
  })
})


test_that("The user cannot manage cameras once they have signed out, and yet they can still read the 'public' data", {
  testServer(public_app$server, {
    login_settings(session)
    session$setInputs(settings_logout = 1)
    expect_false(auth$credentials$result)
    expect_false(auth$can_manage_cameras())
    expect_match(output$results, "Rattus rattus")
  })
})
