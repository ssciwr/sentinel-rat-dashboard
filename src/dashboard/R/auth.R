
fetch_auth_user <- function(user) {
  session <- create_db_session()
  on.exit(session$close())
  account <- app_user_crud$get_login(session, user)
  if (is.null(account)) {
    return(data.frame())
  }
  data.frame(
    app_user_id = as.integer(account$app_user_id),
    user = as.character(account$user),
    password = if (is.null(account$password)) NA_character_ else as.character(account$password),
    is_active = isTRUE(account$is_active),
    stringsAsFactors = FALSE
  )
}


# Hash a password before storing it against a new or existing database user.
set_auth_user_password <- function(user, password) {
  stopifnot(is.character(user), length(user) == 1, !is.na(user), nzchar(trimws(user)),
    is.character(password), length(password) == 1, !is.na(password), nzchar(password))
  session <- create_db_session()
  on.exit(session$close())
  account <- app_user_crud$set_password(
    session, username = user, password = scrypt::hashPassword(password)
  )
  as.integer(account$id)
}
