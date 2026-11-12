# Only signed in users can manage cameras
register_settings_server <- function(input, output, session, fetch_user = fetch_auth_user,
    auth = register_auth_server(input, session, fetch_user)) {
  credentials <- auth$credentials
  can_manage_cameras <- auth$can_manage_cameras
  cameras <- reactiveVal(data.frame())
  adding_camera <- reactiveVal(FALSE)

  output$settings_button <- renderUI({
    if (isTRUE(credentials$result)) return(tagList(icon("gear"), " Settings"))
    tagList(icon("right-to-bracket"), " Sign in/up")
  })

  output$settings_title <- renderText({
    if (!can_manage_cameras()) return("Settings")
    if (adding_camera()) "Add New Camera" else "Edit Existing Camera"
  })

  output$settings_auth <- renderUI({
    req(!isTRUE(credentials$result))
    if (auth$registration()) return(settings_registration_ui())
    settings_login_ui()
  })

  observeEvent(input$settings_logout, {
    cameras(data.frame())
    adding_camera(FALSE)
  })

  output$settings_menu <- renderUI({
    if (isTRUE(credentials$result)) {
      return(tagList(
        tags$li(settings_modal_link("settings_open", "Edit Existing Camera")),
        tags$li(settings_modal_link("camera_add_open", "Add New Camera")),
        tags$li(actionLink("settings_logout", "Log out", class = "dropdown-item"))
      ))
    }
    tagList(
      tags$li(settings_modal_link("settings_open", "Login")),
      tags$li(settings_modal_link("settings_register_open"))
    )
  })

  # for edit mode, prefill fields from existing data.
  update_camera_form <- function(camera = data.frame()) {
    editing <- nrow(camera) == 1
    updateTextInput(session, "camera_name", value = if (editing) camera$camera_name else "")
    updateNumericInput(session, "camera_latitude", value = if (editing) camera$lat else NA)
    updateNumericInput(session, "camera_longitude", value = if (editing) camera$lon else NA)
    updateSelectInput(session, "camera_status", selected = if (editing) camera$status else "active")
  }

  # Refresh camera options without exposing database errors in the dialog.
  refresh_cameras <- function() {
    tryCatch({
      rows <- fetch_camera_settings()
      cameras(rows)
      updateSelectInput(session, "camera_selection", choices = c("Select a camera" = "", setNames(rows$camera_id, rows$camera_name)), selected = "")
    }, error = function(error) {
      message("Camera settings could not be loaded.")
      showNotification("Camera list could not be loaded. Reopen settings to try again.", type = "error")
    })
  }
  observeEvent(list(input$settings_open, can_manage_cameras()), {
    req(can_manage_cameras())
    adding_camera(FALSE)
    refresh_cameras()
    update_camera_form()
  })

  observeEvent(input$camera_add_open, {
    req(can_manage_cameras())
    adding_camera(TRUE)
    update_camera_form()
  })

  output$camera_settings <- renderUI({
    req(credentials$result)
    if (can_manage_cameras()) {
      camera_settings_form(isolate(cameras()), adding = adding_camera())
    } else {
      tags$p("Camera changes require an active, signed-in account.")
    }
  })

  observeEvent(input$camera_selection, {
    req(can_manage_cameras(), !adding_camera())
    camera <- cameras()[cameras()$camera_id == input$camera_selection, , drop = FALSE]
    update_camera_form(camera)
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
    camera_id <- NULL
    if (!adding_camera()) {
      if (!isTRUE(input$camera_selection %in% as.character(cameras()$camera_id))) {
        showNotification("Select an existing camera to edit.", type = "error")
        return()
      }
      camera_id <- as.integer(input$camera_selection)
    }
    tryCatch({
      save_camera_settings(name, coordinates[1], coordinates[2], camera_id, status = status)
      showNotification("Camera saved.", type = "message")
      refresh_cameras()
      updateSelectInput(session, "camera_selection", selected = "")
      update_camera_form()
      session$sendCustomMessage("camera_saved", "camera-settings")
    }, error = function(error) {
      message("Camera settings could not be saved.")
      showNotification("Camera could not be saved. Check that its ID is unique and try again.", type = "error")
    })
  })
}
