library(shiny)

source("R/db.R", local = TRUE)
source("R/auth.R", local = TRUE)
source("server/auth_server.R", local = TRUE)

ui <- fluidPage(
  titlePanel("SENTINEL-RAT Dashboard"),
  mainPanel(
    uiOutput("auth_controls"),
    tableOutput("results")
  )
)

server <- function(input, output, session) {
  auth <- register_auth_server(input, session)
  db_session <- create_db_session()

  session$onSessionEnded(function() {
    db_session$close()
  })

  output$auth_controls <- renderUI({
    if (!isTRUE(auth$credentials$result)) {
      return(shinymanager::auth_ui("settings_login"))
    }
    tagList(
      tags$p(paste("Signed in as", auth$credentials$user)),
      actionButton("settings_logout", "Log out")
    )
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
