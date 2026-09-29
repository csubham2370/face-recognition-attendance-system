$(document).ready(function () {
    function loadDashboard() {
        const url = $("#dashboardConfig").data("url");

        $.ajax({
            url: url,
            type: "GET",
            beforeSend: function () {
                $("#dashboardDate").text("Loading...");},

            success: function (response) {
                if (!response.success) {
                    return;
                }

                // --------------------------
                // Statistics
                // --------------------------

                $("#dashboardDate").text(response.today);
                $("#totalStudents").text(response.total_students);
                $("#presentCount").text(response.present_count);
                $("#absentCount").text(response.absent_count);
                $("#attendancePercentage").text(response.attendance_percentage + "%");
                
                // --------------------------
                // Progress bar
                // --------------------------

                $("#attendanceProgress").css("width",response.attendance_percentage + "%")
                    .text(response.attendance_percentage + "%");

                // --------------------------
                // Recent records
                // --------------------------

                let rows = "";
                if (response.recent_attendance.length === 0) {
                    rows = `
                        <tr>
                            <td colspan="7" class="text-center text-muted">
                                No attendance records available.
                            </td>
                        </tr>
                    `;
                }
                else {
                    $.each(response.recent_attendance,
                        function (index, record) {
                            rows += `
                                <tr>
                                    <td>${index + 1} </td>
                                    <td>${record.student_id}</td>
                                    <td>${record.name}</td>
                                    <td>${record.date}</td>
                                    <td>${record.time}</td>
                                    <td> ${record.confidence}% </td>
                                    <td><span class="badge bg-success">
                                            ${record.status}
                                        </span></td>
                                </tr>
                            `;
                        }
                    );
                }

                $("#recentAttendanceBody").html(rows);
            },
            error: function (xhr) {
                console.log(xhr.responseText);
                $("#recentAttendanceBody").html(`
                    <tr>
                        <td colspan="7" class="text-center text-danger">
                            Unable to load dashboard data.
                        </td>
                    </tr>
                `);
            }

        });

    }

    // Load automatically
    loadDashboard();
    // Refresh dashboard every 30 seconds
    setInterval(loadDashboard,30000);
});
