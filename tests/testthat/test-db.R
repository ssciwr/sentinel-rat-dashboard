test_that("fetch_analyses returns empty list initially", {
  result <- fetch_analyses()
  expect_type(result, "list")
  expect_length(result, 0)
})
