$(function () {
    cardsColoring();
    tableColoring();
    refreshtime();
    // alerting();
});

function cardsColoring() {

    $("div.file-card").each(function () {
        var qc_passed = $(this).find("p.qc-passed-text");

        if (qc_passed == null) {
            $(this).addClass('new');
        }

        else {
            if (qc_passed.text().indexOf('Succeeded') >= 0) {
                $(this).addClass('succeeded');
            }
            else if (qc_passed.text().indexOf('Failed') >= 0) {

                $(this).addClass('failed');

            }
        }

    });

    $("tr").each(function () {
        var qc_passed = $(this).find("td.qc-passed");

        if (qc_passed == null) {
            $(this).addClass('new');
        }

        else {
            if (qc_passed.text().indexOf('Succeeded') >= 0) {
                $(this).addClass('succeeded');
            }
            else if (qc_passed.text().indexOf('Failed') >= 0) {

                $(this).addClass('failed');

            }
        }

    });

}
function tableColoring() {

    $("tr").each(function () {
        var qc_passed = $(this).find("td.qc_passed");

        if (qc_passed == null) {
            $(this).addClass('new');
        }

        else {
            if (qc_passed.text().indexOf('Succeeded') >= 0) {
                $(this).addClass('succeeded');
            }
            else if (qc_passed.text().indexOf('Failed') >= 0) {

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