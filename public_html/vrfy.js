function show_vrfy(item_num) {
if (item_num) { myWin = open("/cgi-bin/admin/vrfy_item.cgi?item_num=" + item_num, "verify","width=250,height=200,status=no,menubar=no,toolbar=no"); }
else { alert("You must enter an Item Number to check."); }
}
