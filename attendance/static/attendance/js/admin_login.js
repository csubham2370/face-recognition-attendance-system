$(document).ready(function () {

    $("#adminLoginForm").submit(function (event) {

        event.preventDefault();

        let username = $("#username").val().trim();

        let password = $("#password").val();

        if (username === "" || password === "") {

            showMessage("Username and password are required.","danger");

            return;
        }

        $("#loginButton").prop("disabled", true).text("Logging in...");

        $.ajax({

            url: $("#adminLoginForm").data("url"),

            type: "POST",

            data: {

                username: username,

                password: password,

                csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val()

            },


            success: function (response) {

                if (response.success) {

                    showMessage(response.message,"success");

                    window.location.href = response.redirect_url;

                }

                else {

                    showMessage(response.message,"danger");
                    $("#loginButton").prop("disabled", false).text("Login");

                }

            },

            error: function () {

                showMessage("Something went wrong. Please try again.","danger");
                $("#loginButton").prop("disabled", false).text("Login");

            }

        });

    });


    function showMessage(message, type) {

        $("#messageBox").removeClass("d-none alert-success alert-danger").addClass("alert-" + type).text(message);

    }

});