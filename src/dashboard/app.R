library(shiny)

source("R/db.R", local = TRUE)
source("R/auth.R", local = TRUE)
source("server/auth_server.R", local = TRUE)
source("server/settings_server.R", local = TRUE)
source("ui/settings.R", local = TRUE)

ui <- bslib::page_navbar(
  title = "SENTINEL-RAT Dashboard",
  theme = bslib::bs_theme(version = 5),
  bslib::nav_panel(
    "Detections",
    tableOutput("results")
  ),
  bslib::nav_spacer(),
  settings_ui()
)

server <- function(input, output, session) {
  auth <- register_auth_server(input, session)
  register_settings_server(input, output, session, auth = auth)
  db_session <- create_db_session()

  session$onSessionEnded(function() {
    db_session$close()
  })

  output$results <- renderTable({

    # Re-run this code every 1 seconds
    invalidateLater(1000, session)

    rows <- fetch_detections(db_session)

    if (is.null(rows) || nrow(rows) == 0) {
      return(data.frame(Message = "No detection results yet."))
    }

    # Convert species lists into comma-separated text
    if ("species" %in% names(rows)) {
      rows$species <- sapply(rows$species, function(x) {
        paste(unlist(x), collapse = ", ")
      })
    }

    # Round confidence values
    for (column in c("confidence", "species_confidence")) {
      if (column %in% names(rows)) {
        rows[[column]] <- round(rows[[column]], 2)
      }
    }

    rows

  }, striped = TRUE, hover = TRUE, bordered = TRUE)
}

shinyApp(ui, server)
