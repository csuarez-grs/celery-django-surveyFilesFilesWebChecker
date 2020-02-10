$(function () {
    cardsColoring();
    tableColoring();
    refreshtime();
    // alerting();
});

function setColorClass(qc_passed, automation_status) {

    if ((automation_status.indexOf('Not started') >= 0)) {
        if (qc_passed.indexOf('Succeeded') >= 0) {
            return 'succeeded';
        } else if (qc_passed.indexOf('Failed') >= 0) {
            return 'failed';
        } else if (qc_passed.indexOf('Running') >= 0) {
            return 'blinking';
        } else {
            return 'new'
        }
    } else {
        if (automation_status.indexOf('Running') >= 0) {
            return 'blinking';
        } else if (automation_status.indexOf('Success') >= 0) {
            return 'succeeded';
        } else if (automation_status.indexOf('Failure') >= 0) {
            return 'failed';
        } else {
            return null
        }
    }
}

function cardsColoring() {

    $("div.file-card").each(function () {
        var qc_passed = $(this).find("p.qc-passed-text").text();
        var automation_status = $(this).find("p.automation-status-text").text();

        var colorClass = setColorClass(qc_passed, automation_status);

        if (colorClass != null) {
            $(this).addClass(colorClass);
        }
    });
}

function tableColoring() {

    $("tr").each(function () {
        var qc_passed = $(this).find("td.qc_passed").text();
        var automation_status = $(this).find("td.automation_status").text();


        var colorClass = setColorClass(qc_passed, automation_status);

        if (colorClass != null) {
            $(this).addClass(colorClass);
        }

        if (qc_passed.indexOf('—') >= 0) {
            $(this).addClass('new');
        } else {
            if (qc_passed.indexOf('Succeeded') >= 0) {
                $(this).addClass('succeeded');
            } else if (qc_passed.indexOf('Failed') >= 0) {

                $(this).addClass('failed');

            }
        }

    });

}

function refreshtime() {
    var dt = new Date();
    var weekday = new Array(7);
    weekday[0] = "Sunday";
    weekday[1] = "Monday";
    weekday[2] = "Tuesday";
    weekday[3] = "Wednesday";
    weekday[4] = "Thursday";
    weekday[5] = "Friday";
    weekday[6] = "Saturday";

    const monthNames = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    var dayofweek = weekday[dt.getDay()];

    var time = new Date().getHours();
    var greeting;
    if (time < 12) {
        greeting = "Good morning";
    } else if (time < 18) {
        greeting = "Good afternoon";
    } else {
        greeting = "Good evening";
    }

    greeting += '. Checked at ' + ("0" + dt.getHours()).slice(-2) + ":" + ("0" + dt.getMinutes()).slice(-2)
        + ":" + ("0" + dt.getSeconds()).slice(-2)
        + ' ' + dayofweek + ', ' + monthNames[dt.getMonth()] + ', ' + dt.getDate();

    document.getElementById("refreshtime").innerHTML = greeting;
}

function alerting() {
    $('.alerts').each(function () {

        var pc_info = $(this).text();

        if (pc_info.indexOf('Failed') >= 0) {
            $(this).addClass('flashing');
        }

    })
}


$(document).ready(function () {

    $("#id_document").on("change", function () {
        var doc_input = document.getElementById('id_document');
        var fileName = doc_input.value;
        var fileExt = fileName.substring(fileName.lastIndexOf('.') + 1).toLowerCase();
        console.log(fileExt);
        if (fileExt === 'jxl') {
            $("#id_extract_input_values").prop('checked', true);
            $("#id_extract_input_values").prop('disabled', false);
        } else {
            $("#id_extract_input_values").prop('checked', false);
            $("#id_extract_input_values").prop('disabled', true);
        }

    });

    $("#id_create_client_report").on("change", function () {
        var create_report_checked = $('#id_create_client_report').prop('checked');
        console.log(create_report_checked);
        if (create_report_checked) {
            $("#id_create_gis_data").prop('checked', true);
        }
    })

});