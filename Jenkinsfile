// Ensure Python 3 is installed and accessible via the PATH on the Windows agent.
pipeline {
    // Specify the agent/node label for your Windows machine
    agent { label 'windows' } 
    // If you don't use labels, use: agent any

    environment {
        // Jenkins automatically provides $BUILD_NUMBER
        REPORT_DIR = 'reports'
        HISTORY_DIR = 'reports/report_history'
    }

    stages {
        stage('Initialize Environment') {
            steps {
                // Use a standard Windows command step to ensure directories exist
                bat "mkdir %REPORT_DIR%\\report_history"
            }
        }
        
        stage('Run Analysis Script') {
            steps {
                // 1. Run the Python script, passing the Jenkins BUILD_NUMBER
                echo "Running firmware monitor for build #${BUILD_NUMBER}"
                // Use 'bat' command since 'python' is usually found in the system PATH
                bat "python firmware_monitor.py %BUILD_NUMBER%"

                // 2. Find the latest generated report (PowerShell)
                powershell """
                    # Find the newest HTML report and store its path
                    \$LatestReport = Get-ChildItem -Path "${REPORT_DIR}/*.html" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
                    \$env:LATEST_REPORT_PATH = \$LatestReport.FullName
                    
                    # Copy the latest report to index.html for the main page
                    Copy-Item \$env:LATEST_REPORT_PATH -Destination "${REPORT_DIR}/index.html"
                    
                    # Copy the latest report to the history archive
                    Copy-Item \$env:LATEST_REPORT_PATH -Destination "${HISTORY_DIR}/"
                    
                    Write-Host "Latest report path: \$env:LATEST_REPORT_PATH"
                """
            }
        }
        
        stage('Generate History Index') {
            steps {
                // 3. Generate the browsable index page for the history folder (PowerShell)
                powershell """
                    Write-Host "Generating history index page..."
                    
                    \$ReportFiles = Get-ChildItem -Path "${HISTORY_DIR}/*.html" | Sort-Object Name -Descending
                    \$HistoryLinks = ""
                    
                    foreach (\$File in \$ReportFiles) {
                        \$FileName = \$File.Name
                        # Regex to extract Date/Time/Build number from filename
                        \$LinkName = \$FileName -replace "firmware_analysis_report_(\\d{8})_(\\d{6})_(\\d+).html", "Report Date: \$1 Time: \$2 Build: \$3"
                        # Use backticks (`) for escaping quotes within the string
                        \$HistoryLinks += "<li><a href=\`"\$FileName\`">\$LinkName</a></li>\`n"
                    }

                    # Read the history_template.html and replace the placeholder
                    \$TemplateContent = Get-Content "history_template.html" -Raw
                    \$NewContent = \$TemplateContent -replace '\\\$HISTORY_LINKS', \$HistoryLinks
                    
                    # Write the final index file
                    Set-Content -Path "${HISTORY_DIR}/index.html" -Value \$NewContent
                    
                    Write-Host "History index created successfully."
                """
            }
        }

        stage('Archive Reports') {
            steps {
                // Archives the reports directory within Jenkins
                archiveArtifacts artifacts: "${REPORT_DIR}/**", fingerprint: true
            }
        }
    }
    
    post {
        always {
            // Optional: Publish HTML reports using the HTML Publisher Plugin
            // Requires the HTML Publisher plugin to be installed on your Jenkins instance.
            // publishHtml(target: [
            //     allowMissing: false,
            //     alwaysLinkToLastBuild: true,
            //     keepAll: true,
            //     reportDir: REPORT_DIR,
            //     reportFiles: 'index.html',
            //     reportName: 'Firmware Analysis Report'
            // ])
            
            // Cleanup work files if necessary
            cleanWs()
        }
    }
}