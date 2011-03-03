<html>
<head><title>modbus-tk - Master HMI</title>
<link rel="stylesheet" type="text/css" href="/media/style.css" media="all" />
<script type="text/javascript" src="/media/jquery-1.4.2.min.js"></script>
<script>
$(document).ready(function () {
	$("#add-req-form").hide();
	
	show_add_request_form = function() {
		$("#add-req-link").hide();
		$("#add-req-form").show("fast");
	};
	
	hide_add_request_form = function() {
		$("#add-req-link").show();
		$("#add-req-form").hide();
	};
	
	delete_request = function(master, id) {
		if (confirm('Do you want to delete request '+id+'?')) {
			window.location = '/delete-request/'+master+'/'+id;
		}
	};
});
</script>
</head>
<body>
<div id="main">
<h1>Modbus Master {{master.id}} - {{master.address}}</h1>

<table class="breadcrumbs"><tr>
	<td><a href="/masters">Masters</a></td>
	<td>></td>
	<td><a href="/master/{{master.id}}">{{master.address}}</a></td>
</tr></table>

<table class="all">
	<tr>
        <td>
            <table class="master">
            %for req in master.requests:
                <tr>
                    <td>{{req['name']}}</td>
                    <td><a href="/modbus-read/{{master.id}}/{{req['slave']}}/{{req['function']}}/{{req['address']}}/{{req['length']}}">view</a></td>
                    <td><a href="javascript:delete_request({{master.id}}, {{req['id']}})">delete</a></td>
                    <td></td>
                </tr>
            %end
            %for req in master.get_slaves():
                <tr>
                    <td colspan="3"><a href="/modbus-read-all-hr/{{master.id}}/{{req['slave']}}">All Holding Registers for Slave: {{req['slave']}}</a></td>
                </tr>
            %end
                <tr>
                    <td colspan="3"></td>
                    <td id="addreq">
                        <a href="javascript:show_add_request_form()" id="add-req-link">add</a>
                        <form method="POST" id="add-req-form" action="/add-request/{{master.id}}">
                        <table>
                            <tr><th>Slave</th><td><INPUT type="text" value="1" name="slave"/></td></tr>
                            <tr><th>Function Code</th>
                                <td>
                                    <SELECT name="function">                                       
                                        <OPTION VALUE="1">Read Coils</OPTION>
                                        <OPTION VALUE="3">Read Holding Registers</OPTION>
                                        <OPTION VALUE="4">Read Input Registers</OPTION> 
                                    </SELECT>
                                </td>
                            </td></tr>
                            <tr><th>Starting Address</th><td><INPUT type="text" value="0" name="address"/></td></tr>
                            <tr><th>length</th><td><INPUT type="text" value="16" name="length"/></td></tr>
                            <tr><td><a href="javascript:hide_add_request_form()">Cancel</a></td><td><input type="submit" value="OK"/></td></tr>
                        </table>
                        </form>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
</table>
</div>
</body>
</html>