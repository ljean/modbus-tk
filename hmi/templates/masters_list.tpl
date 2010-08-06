<html>
<head><title>modbus-tk - Master HMI</title>
<link rel="stylesheet" type="text/css" href="/media/style.css" media="all" />
<script type="text/javascript" src="/media/jquery-1.4.2.min.js"></script>
<script>
$(document).ready(function () {
	$("#add-master-form").hide();
	show_add_master_form = function() {
		$("#add-master-link").hide();
		$("#add-master-form").show("fast");
	};
	
	hide_add_master_form = function() {
		$("#add-master-link").show();
		$("#add-master-form").hide();
	};
		
	delete_master = function(id) {
		if (confirm('Do you want to delete master '+id+'?')) {
			window.location = '/delete-master/'+id;
		}
	};
	
	var selector = $('#protocol');
	selector.change(function() {
	    if (selector.val() == "tcp") {
	        $("#server_address").val("0.0.0.0");
	 	} else {
	    	$("#server_address").val("0");
	    }
	});
});
</script>
</head>
<body>
<div id="main">
<h1>Modbus Masters</h1>
<table class="breadcrumbs"><tr>
	<td><a href="/masters">Masters</a></td>
</tr></table>

<table class="master">
	%for master in masters:
	<tr>
	<td>{{master.id}}</td>
	<td><a href="/master/{{master.id}}">{{master.protocol}} - {{master.address}}</a></td>
	<td><a href="javascript:delete_master({{master.id}})">delete</a></td>
	</tr>
	
	%end
	<tr><td colspan="3"></td>
		<td id="addslave">
			<a href="javascript:show_add_master_form()" id="add-master-link">add</a>
			<form method="POST" id="add-master-form" action="/add-master">
			<table>
				<tr><th>Protocol</th>
				<td><SELECT name="protocol" id="protocol">
					<OPTION VALUE="tcp">TCP</OPTION>
					<OPTION VALUE="rtu">RTU</OPTION>
				</SELECT></td></tr>
				<tr><th>Server Address</th><td><INPUT type="text" value="0.0.0.0" id="server_address" name="server_address"/></td></tr>
				<tr><td><a href="javascript:hide_add_master_form()">Cancel</a></td><td><input type="submit" value="OK"/></td></tr>
			</table>
			</form>
		</td>
	</tr>
</table>
</div>
</body>
</html>