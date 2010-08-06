<html>
<head><title>modbus-tk - Master HMI - Result of query {{name}}</title>
<link rel="stylesheet" type="text/css" href="/media/style.css" media="all" />
<script type="text/javascript" src="/media/jquery-1.4.2.min.js"></script>
<script>
$(document).ready(function () {
    var poll_rate = 1000;
    var timer_id = get_data(poll_rate);
    var isPolling = true;

    $('.result').each(function(index, element) {
        var register_id = "#" + this.id + "_decimal";
        var register = parseInt($(register_id).text());
        $("#" + this.id + "_0based").text(register + 400000);
        $("#" + this.id + "_1based").text(register + 400001);
    });

    $("#enable_polling").hide();

    $('#disable_polling').click(function() 
        {
            clearInterval(timer_id);
            isPolling = false;
            $(this).hide();
            $("#enable_polling").show();
        }
    ).hover(function() {
            $(this).addClass("hover");
        },
        function() {
            $(this).removeClass("hover");
        }
    );
    $('#enable_polling').click(function()
        {
            timer_id = get_data(poll_rate);
            isPolling = true;
            $(this).hide();
            $("#disable_polling").show();
        }
    ).hover(function() {
            $(this).addClass("hover");
        },
        function() {
            $(this).removeClass("hover");
        }
    );

    $("#poll_rate_input").keyup(function() {
        poll_rate = parseInt($(this).val()) * 1000;
        if (isPolling)
        {
            clearInterval(timer_id);
            timer_id = get_data(poll_rate);
        }
    });

});

function get_data(poll_rate) {
    var timer_id = setInterval(function(){
    var start_time = new Date().getTime();
    $("#start_time").text(start_time);
    json_url = '{{url}}'.replace('modbus-read', 'modbus-read-json');
    $.getJSON(json_url, function(data) {
        $.each(data, function(name, value){
            var item = $('#'+name);
            item.text(value);
        });
    });

    $('.result').each(function(index, element) {
        var dec_val = parseInt($('#' + this.id).text());
        var bin_val = dec_val.toString(2);
        var hex_val = dec_val.toString(16);
        $("#" + this.id + "_hex").text('0x' + hex_val);
        for (i=16; i>0; i=i-1)
        {
            var current_node = $("#" + this.id + "_binary" + i);
            if (i > bin_val.length)
            {
                $(current_node).text(0);
                $(current_node).addClass("binary_off");
                $(current_node).removeClass("binary_on");
            }
            else
            {
                $(current_node).text(bin_val[bin_val.length - i]);
                if ($(current_node).text() === "1")
                {
                    $(current_node).addClass("binary_on");
                    $(current_node).removeClass("binary_off");
                }
                else
                {
                    $(current_node).addClass("binary_off");
                    $(current_node).removeClass("binary_on");
                }
            }
        }
    });
    var finish_time = new Date().getTime();
    $("#finish_time").text(finish_time);
    $("#execution_time").text(finish_time - start_time);
    }, poll_rate);


    return timer_id;
};

</script>
</head>
<body>
<div id="main">
<h1>Results of request {{friendly_name}}</h1>
<table class="breadcrumbs"><tr>
	<td><a href="/masters">Masters</a></td>
	<td>></td>
	<td><a href="/master/{{master.id}}">{{master.address}}</a></td>
	<td>></td>
	<td><a href="{{url}}">{{friendly_name}}</a></td>
</tr></table>
<div id="polling_commands">
    <p id="enable_polling">Enable Polling</p>
    <p id="disable_polling">Disable Polling</p>
    <form>
        <label for="poll_rate_input">Poll Rate (sec)</label>
        <input type="text" name="poll_rate_input" id="poll_rate_input" value="1"/>
    </form>
    <p>Start Time: <span id="start_time">0</span></p>
    <p>Finish Time: <span id="finish_time">0</span></p>
    <p>Execution Time: <span id="execution_time">0</span></p>
</div>
<table class="results">
	<tr>
        <th style="width:50px;" rowspan="2">Register (dec)</th>
        <th style="width:50px;" rowspan="2">Register (hex)</th>
        <th style="width:50px;" rowspan="2">Modbus Register (0 Based)</th>
        <th style="width:50px;" rowspan="2">Modbus Register (1 Based)</th>
        <th style="width:50px;" rowspan="2">Value</th>
        <th style="width:50px;" rowspan="2">Hex Value</th>
        <th style="width:350px;" colspan="16">Binary Value</th>
	</tr>
    <tr>
        <th>16</th>
        <th>15</th>
        <th>14</th>
        <th>13</th>
        <th>12</th>
        <th>11</th>
        <th>10</th>
        <th>9</th>
        <th>8</th>
        <th>7</th>
        <th>6</th>
        <th>5</th>
        <th>4</th>
        <th>3</th>
        <th>2</th>
        <th>1</th>
    </tr>
    %i=0
        %for register in results:
        <tr>
            <td class="register_decimal" id="{{register}}_decimal">{{register}}</td>
            <td class="register_hex">{{results[register]['register_hex']}}</td>
            <td class="register_0based" id="{{register}}_0based">{{register}}</td>
            <td class="register_1based" id="{{register}}_1based">{{register}}</td>
            <td class="result" id="{{register}}">{{results[register]['result']}}</td>
            <td class="result_binary" id="{{register}}_hex"></td>
            <td class="result_binary" id="{{register}}_binary16"></td>
            <td class="result_binary" id="{{register}}_binary15"></td>
            <td class="result_binary" id="{{register}}_binary14"></td>
            <td class="result_binary" id="{{register}}_binary13"></td>
            <td class="result_binary" id="{{register}}_binary12"></td>
            <td class="result_binary" id="{{register}}_binary11"></td>
            <td class="result_binary" id="{{register}}_binary10"></td>
            <td class="result_binary" id="{{register}}_binary9"></td>
            <td class="result_binary" id="{{register}}_binary8"></td>
            <td class="result_binary" id="{{register}}_binary7"></td>
            <td class="result_binary" id="{{register}}_binary6"></td>
            <td class="result_binary" id="{{register}}_binary5"></td>
            <td class="result_binary" id="{{register}}_binary4"></td>
            <td class="result_binary" id="{{register}}_binary3"></td>
            <td class="result_binary" id="{{register}}_binary2"></td>
            <td class="result_binary" id="{{register}}_binary1"></td>
            %i=i+1
        </tr>
        %end
	%end
</table>
</div></body>
</html>