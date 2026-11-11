# Only signed in users can manage cameras
register_settings_server <- function(input, output, session, fetch_user = fetch_auth_user,
    auth = register_auth_server(input, session, fetch_user)) {
  credentials <- auth$credentials
  can_manage_cameras <- auth$can_manage_cameras
  cameras <- reactiveVal(data.frame())

  output$settings_auth <- renderUI({
    req(!isTRUE(credentials$result))
    if (auth$registration()) return(settings_registration_ui())
    settings_login_ui()
  })

  observeEvent(input$settings_logout, {
    cameras(data.frame())
  })

  output$settings_menu <- renderUI({
    label <- "Login"
    if (isTRUE(credentials$result)) {
      label <- "Camera settings"
    }
    tagList(
      tags$li(actionLink("settings_open", label, class = "dropdown-item",
        `data-bs-toggle` = "modal", `data-bs-target` = "#camera-settings")),
      if (!isTRUE(credentials$result)) tags$li(account_registration_link("settings_register_open"))
    )
  })

  # Refresh camera options without exposing database errors in the dialog.
  refresh_cameras <- function() {
    tryCatch({
      rows <- fetch_camera_settings()
      cameras(rows)
      updateSelectInput(session, "camera_selection", choices = c("New camera" = "", setNames(rows$camera_id, rows$camera_name)))
    }, error = function(error) {
      message("Camera settings could not be loaded.")
      showNotification("Camera list could not be loaded. Reopen settings to try again.", type = "error")
    })
  }
  observeEvent(list(input$settings_open, can_manage_cameras()), {
    if (can_manage_cameras()) refresh_cameras()
  })

  output$camera_settings <- renderUI({
    req(credentials$result)
    content <- if (can_manage_cameras()) {
      camera_settings_form(isolate(cameras()))
    } else {
      tags$p("Camera changes require an active, signed-in account.")
    }
    tagList(content, actionButton("settings_logout", "Log out"))
  })

  observeEvent(input$camera_selection, {
    req(can_manage_cameras())
    camera <- cameras()[cameras()$camera_id == input$camera_selection, , drop = FALSE]
    editing <- nrow(camera) == 1
    updateTextInput(session, "camera_name", value = if (editing) camera$camera_name else "")
    updateNumericInput(session, "camera_latitude", value = if (editing) camera$lat else NA)
    updateNumericInput(session, "camera_longitude", value = if (editing) camera$lon else NA)
    updateSelectInput(session, "camera_status", selected = if (editing) camera$status else "active")
  }, ignoreNULL = FALSE)

  observeEvent(input$camera_save, {
    if (!can_manage_cameras()) {
      showNotification("Camera access could not be confirmed. Sign in again or try later.", type = "error")
      return()
    }
    name <- trimws(input$camera_name)
    coordinates <- c(input$camera_latitude, input$camera_longitude)
    if (length(name) != 1 || !nzchar(name) || nchar(name) > 255 || length(coordinates) != 2 ||
        any(!is.finite(coordinates)) || abs(coordinates[1]) > 90 || abs(coordinates[2]) > 180) {
      showNotification("Enter a Camera ID, latitude (-90 to 90), and longitude (-180 to 180).", type = "error")
      return()
    }
    status <- input$camera_status
    if (length(status) != 1 || is.na(status) || !status %in% c("active", "inactive")) {
      showNotification("Choose a valid camera status.", type = "error")
      return()
    }
    tryCatch({
      camera_id <- NULL
      if (nzchar(input$camera_selection)) camera_id <- as.integer(input$camera_selection)
      saved_id <- save_camera_settings(name, coordinates[1], coordinates[2], camera_id, status = status)
      showNotification("Camera saved.", type = "message")
      refresh_cameras()
      updateSelectInput(session, "camera_selection", selected = as.character(saved_id))
    }, error = function(error) {
      message("Camera settings could not be saved.")
      showNotification("Camera could not be saved. Check that its ID is unique and try again.", type = "error")
    })
  })
}
