$(document).ready(function () {

    $("#trainModelButton").click(function () {

        let trainButton = $("#trainModelButton");

        let trainUrl = trainButton.data("url");

        let csrfToken = $("input[name=csrfmiddlewaretoken]").val();

        trainButton.prop("disabled", true).text("Training...");

        $("#trainingMessage").removeClass().addClass("mt-3 alert alert-info").text("Model training started...");

        $.ajax({

            url: trainUrl,

            type: "POST",

            data: {csrfmiddlewaretoken: csrfToken},

            success: function (response) {

                if (response.success) {

                    $("#trainingMessage").removeClass().addClass("mt-3 alert alert-success").text(response.message);

               
                    let accuracy = response.result.accuracy * 100;
                    let validationAccuracy = response.result.validation_accuracy * 100;


                    $("#trainingMessage").removeClass().addClass("mt-3 alert alert-success")
                    .html("Model trained successfully.<br>" +
                            "Training Accuracy: " +
                            accuracy.toFixed(2) +
                                 "%<br>" +
                            "Validation Accuracy: " + validationAccuracy.toFixed(2) + "%");
               
                }

                else {

                    $("#trainingMessage").removeClass().addClass("mt-3 alert alert-danger").text(response.message);

                }

                trainButton.prop("disabled", false).text("Train Model");
            },


            error: function (xhr) {

                let message = xhr.responseJSON?.message || "Model training failed.";

                $("#trainingMessage").removeClass().addClass( "mt-3 alert alert-danger").text(message);

                trainButton.prop("disabled", false).text("Train Model");

            }

        });

    });

});