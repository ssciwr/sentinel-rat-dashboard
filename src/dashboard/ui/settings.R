# Contains the login/register options
settings_ui <- function() {
  bslib::nav_item(
    div(class = "dropdown",
      tags$button(
        type = "button", class = "btn btn-outline-secondary btn-sm dropdown-toggle",
        `data-bs-toggle` = "dropdown", `aria-expanded` = "false",
        uiOutput("settings_button", inline = TRUE)
      ),
      uiOutput("settings_menu", container = tags$ul, class = "dropdown-menu dropdown-menu-end")
    ),
    div(id = "camera-settings", class = "modal fade", tabindex = "-1",
      role = "dialog", `aria-labelledby` = "camera-settings-title",
      div(class = "modal-dialog", div(class = "modal-content",
        div(class = "modal-header",
          tags$h4(id = "camera-settings-title", class = "modal-title", textOutput("settings_title", inline = TRUE)),
          tags$button(type = "button", class = "btn-close", `data-bs-dismiss` = "modal", `aria-label` = "Close")
        ),
        div(class = "modal-body",
          uiOutput("settings_auth"),
          uiOutput("camera_settings")
        )
      ))
    ),
    tags$script(HTML("
      Shiny.addCustomMessageHandler('camera_saved', function(modalId) {
        bootstrap.Modal.getInstance(document.getElementById(modalId))?.hide();
      });
    "))
  )
}
settings_login_ui <- function() {
  login <- htmltools::tagQuery(shinymanager::auth_ui("settings_login"))
  login <- login$filter(".panel-auth")$removeClass("panel-auth")
  login$find(".row > .col-sm-4")$removeAttrs("class")$addClass("col-12")$allTags()
}

settings_modal_link <- function(id, label = "Create account", class = "dropdown-item") {
  actionLink(id, label, class = class,
    `data-bs-toggle` = "modal", `data-bs-target` = "#camera-settings")
}

settings_registration_ui <- function() {
  tagList(
    tags$h4("Create account"),
    textInput("settings_register_user", "Username"),
    passwordInput("settings_register_password", "Password"),
    passwordInput("settings_register_password_confirm", "Confirm password"),
    div(class = "mb-3", actionButton("settings_create_account", "Create account", class = "btn-primary")),
    actionLink("settings_login_open", "Back to login")
  )
}

# The original camera edit form - sorry, this was added and then removed and then added back here as it made sense to be in this file, since the user doesn't particualrly need to be on the map view to edit cameras, and there was no where that worked well aesthetically on the map itself to have a general Add camera form / button
camera_settings_form <- function(cameras, adding = FALSE) {
  tagList(
    # let's you select the camera to edit - when clicked it uses the camera_id but displays the cameraId.
    if (!adding) selectInput("camera_selection", "Camera", c("Select a camera" = "", setNames(cameras$camera_id, cameras$camera_name)), selectize = FALSE),
    textInput("camera_name", "Camera ID"),
    numericInput("camera_latitude", "Latitude", value = NA, min = -90, max = 90),
    numericInput("camera_longitude", "Longitude", value = NA, min = -180, max = 180),
    selectInput("camera_status", "Status", c("Active" = "active", "Inactive" = "inactive"), selected = "active", selectize = FALSE),
    actionButton("camera_save", if (adding) "Create camera" else "Save camera", class = "btn-primary")
  )
}
