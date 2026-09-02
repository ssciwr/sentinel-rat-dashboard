library(shiny)
library(DBI)

ui <- fluidPage(
  titlePanel("SENTINEL-RAT Dashboard"),
  mainPanel(
    tableOutput("results")
  )
)

server <- function(input, output, session) {
  db_session <- create_db_session()

  session$onSessionEnded(function() {
    db_session$close()
  })

  output$results <- renderTable({

    # Re-run this code every 1 seconds
    invalidateLater(1000, session)

    rows <- fetch_detections(db_session)

    if (is.null(rows) || nrow(rows) == 0) {
      return(data.frame(Message = "No analysis results yet."))
    }

    # Convert species lists into comma-separated text
    if ("species" %in% names(rows)) {
      rows$species <- sapply(rows$species, function(x) {
        paste(unlist(x), collapse = ", ")
      })
    }

    # Round confidence values
    if ("confidence" %in% names(rows)) {
      rows$confidence <- round(rows$confidence, 2)
    }

    rows

  }, striped = TRUE, hover = TRUE, bordered = TRUE)
}

shinyApp(ui, server)