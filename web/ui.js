var apiurl = "api.py";
var loadedtransactions = [];
var accountsearches = [ {} ];
var showing = -1;
var showtrans = {};
var editedfields = []
var limit = 25;
var skip = 0;
var query = accountsearches[0];
var sessioncheckinterval = null;
var categories = {};
var allcategories = [];
var centers = [];
var tags = [];
var linkparent = "";
var linkchildren = [];
var chart = null;
var curreport = -1;

var reportopts = {
    "spendcategory": {
        "defstart": (new Date((new Date()).getFullYear(),(new Date()).getMonth()-1,1)).toISOString().substr(0,10),
        "defend": (new Date((new Date()).getFullYear(),(new Date()).getMonth(),0)).toISOString().substr(0,10),
        "filter": {"amount": "$lt:0"},
        "filterout": {},
        "key": "category",
        "keydef": "Uncategorized",
        "keysort": "amount",
        "keysortrev": false,
        "subkey": "subcategory",
        "subkeydef": "None",
        "subkeysort": "amount",
        "subkeysortrev": false,
        "title": "Spending by Category",
        "type": "pie",
        getseries: getpiedata,
        getsettings: function(data, months) { return {}; },
    },
    "incomecategory": {
        "defstart": (new Date((new Date()).getFullYear(),(new Date()).getMonth()-1,1)).toISOString().substr(0,10),
        "defend": (new Date((new Date()).getFullYear(),(new Date()).getMonth(),0)).toISOString().substr(0,10),
        "filter": {"amount": "$gt:0"},
        "filterout": {},
        "key": "category",
        "keydef": "Uncategorized",
        "keysort": "amount",
        "keysortrev": true,
        "subkey": "subcategory",
        "subkeydef": "None",
        "subkeysort": "amount",
        "subkeysortrev": true,
        "title": "Income by Category",
        "type": "pie",
        getseries: getpiedata,
        getsettings: function(data, months) { return {}; },
    },
    "spendingtrend": {
        "defstart": (new Date((new Date()).getFullYear(),0,1)).toISOString().substr(0,10),
        "defend": (new Date((new Date()).getFullYear(),(new Date()).getMonth(),0)).toISOString().substr(0,10),
        "filter": {"amount": "$lt:0"},
        "filterout": {},
        "key": "category",
        "keydef": "Uncategorized",
        "keysort": "amount",
        "keysortrev": "false",
        "subkey": "month",
        "subkeydef": "",
        "subkeysort": "name",
        "subkeysortrev": false,
        "title": "Spending Trend",
        "type": "column",
        getseries: function (data, months) { return []; },
        getsettings: gettrendsettings,
    },
    "incometrend": {
        "defstart": (new Date((new Date()).getFullYear(),0,1)).toISOString().substr(0,10),
        "defend": (new Date((new Date()).getFullYear(),(new Date()).getMonth(),0)).toISOString().substr(0,10),
        "filter": {"amount": "$gt:0"},
        "filterout": {},
        "key": "category",
        "keydef": "Uncategorized",
        "keysort": "amount",
        "keysortrev": "false",
        "subkey": "month",
        "subkeydef": "",
        "subkeysort": "name",
        "subkeysortrev": false,
        "title": "Income Trend",
        "type": "column",
        getseries: function (data, months) { return []; },
        getsettings: gettrendsettings,
    },
    "totaltrend": {
        "defstart": (new Date((new Date()).getFullYear(),0,1)).toISOString().substr(0,10),
        "defend": (new Date((new Date()).getFullYear(),(new Date()).getMonth(),0)).toISOString().substr(0,10),
        "filter": {"amount": "$ne:0"},
        "filterout": {},
        "key": "category",
        "keydef": "Uncategorized",
        "keysort": "amount",
        "keysortrev": "false",
        "subkey": "month",
        "subkeydef": "",
        "subkeysort": "name",
        "subkeysortrev": false,
        "title": "Net Income Trend",
        "type": "column",
        getseries: function (data, months) {
            var monthnames = [];
            var monthtotals = [];
            var series = [];
            for (i in data) {
                for (j in data[i]["subs"])
                    if (monthnames.indexOf(data[i]["subs"][j]["name"]) == -1) {
                        monthnames.push(data[i]["subs"][j]["name"]);
                    }
            }
            monthnames.sort();
            for (i in monthnames)
                monthtotals.push({"name": monthnames[i], "amount": 0})
            for (i in data) {
                data[i].data = [];
                for (j in monthnames)
                    data[i].data.push(0);
                for (j in data[i]["subs"]) {
                    data[i].data[monthnames.indexOf(data[i]["subs"][j]["name"])] = data[i]["subs"][j]["amount"];
                    monthtotals[monthnames.indexOf(data[i]["subs"][j]["name"])]["amount"] += data[i]["subs"][j]["amount"];
                }
            }
            data.push({type: 'spline', name: 'Total', subs: monthtotals});
            return [];
        },
        getsettings: gettrendsettings,
    },
    "squashcenter": {
        "defstart": (new Date((new Date()).getFullYear(),0,1)).toISOString().substr(0,10),
        "defend": (new Date((new Date()).getFullYear(),(new Date()).getMonth(),0)).toISOString().substr(0,10),
        "filter": {"amount": "$ne:0"},
        "filterout": {},
        "key": "category",
        "keydef": "Uncategorized",
        "keysort": "amount",
        "keysortrev": "false",
        "subkey": "month",
        "subkeydef": "",
        "subkeysort": "name",
        "subkeysortrev": false,
        "modify": "center",
        "title": "Net Income Trend",
        "type": "column",
        getseries: function (data, months) {
            var monthnames = [];
            var monthtotals = [];
            var series = [];
            for (i in data) {
                for (j in data[i]["subs"])
                    if (monthnames.indexOf(data[i]["subs"][j]["name"]) == -1) {
                        monthnames.push(data[i]["subs"][j]["name"]);
                    }
            }
            monthnames.sort();
            for (i in monthnames)
                monthtotals.push({"name": monthnames[i], "amount": 0})
            for (i in data) {
                data[i].data = [];
                for (j in monthnames)
                    data[i].data.push(0);
                for (j in data[i]["subs"]) {
                    data[i].data[monthnames.indexOf(data[i]["subs"][j]["name"])] = data[i]["subs"][j]["amount"];
                    monthtotals[monthnames.indexOf(data[i]["subs"][j]["name"])]["amount"] += data[i]["subs"][j]["amount"];
                }
            }
            data.push({type: 'spline', name: 'Total', subs: monthtotals});
            return [];
        },
        getsettings: gettrendsettings,
    }
}

// "nice" jQueryUI popup message
function showerror(err) {
    $("#errormsg").text(err);
    $("#errormsg").dialog("open");
}

// After login, reset everything
function loginsuccess() {
    $("#login").hide();
    $("#searchoptions").show();
    $("#linktransactions").show();
    $("#reports").show();
    $("#linktransactions").width($("#searchoptions").width())
    $("#linktransactions").css("top", $("#searchoptions").offset().top+$("#searchoptions").height()+10)
    $("#reports").width($("#searchoptions").width());
    $("#reports").css("top", $("#linktransactions").offset().top+$("#linktransactions").height()+10)
    $("#reports").css("left", $("#linktransactions").offset().left);
    $("#searchoptions .searchoption").each(function () { $(this).val(""); });
    $("#searchoptions .queryoption").each(function () { $(this).val(""); });
    clearlink();
    loadedtransactions = [];
    showing = -1;
    limit = 25;
    skip = 0;
    loadaccounts();
    // Get user's categories and configure everywhere
    $.ajax({
        type: "POST",
        url: apiurl,
        data: { "action": "getcategories" },
        success: function (data) {
            categories = data;
            allcategories = []
            for (cat in categories) {
                allcategories.push(cat);
                allcategories = allcategories.concat(categories[cat]);
            }
            allcategories.sort();
            keys = Object.keys(categories);
            keys.sort();
            $(".category").autocomplete({
                source: keys,
                delay: 0,
                minLength: 0,
                select: function(event, ui) {
                    if ($(this).hasClass("transdataval")) {
                        $("#transactiondetail .savebutton").button("enable");
                        if (editedfields.indexOf("category") == -1)
                            editedfields.push("category");
                    }
                    $(this).parent().children(".subcategory").autocomplete("option", "source", categories[ui.item.value]);
                },
                change: function(event, ui) {
                    var newauto = categories[$(this).val()];
                    if (newauto == undefined)
                        newauto = allcategories;
                    $(this).parent().children(".subcategory").autocomplete("option", "source", newauto);
                }
            });
            $(".subcategory").autocomplete({
                source: allcategories,
                delay: 0,
                minLength: 0,
                select: function(event, ui) {
                    if ($(this).hasClass("transdataval")) {
                        if (editedfields.indexOf("subcategory") == -1)
                            editedfields.push("subcategory");
                        $("#transactiondetail .savebutton").button("enable");
                    }
                    catval = $(this).parent().children(".category").val();
                    if ((catval == "") || (categories[catval] == undefined) || (categories[catval].indexOf(ui.item.value) == -1)) {
                        if (categories[ui.item.value] != undefined) {
                            $(this).parent().children(".category").val(ui.item.value);
                            $(this).val("");
                            return false;
                        }
                        for (cat in categories) {
                            if (categories[cat].indexOf(ui.item.value) != -1) {
                                $(this).parent().children(".category").val(cat);
                                if ($(this).hasClass("transdataval")) {
                                    if (editedfields.indexOf("category") == -1)
                                        editedfields.push("category");
                                    $("#transactiondetail .savebutton").button("enable");
                                }
                                break;
                            }
                        }
                    }
                }
            });
        },
        error: function () {
            showerr("Error loading categories!");
        }
    });
    // Get user's cost centers, load up elements.
    $.ajax({
        type: "POST",
        url: apiurl,
        data: { "action": "getcenters" },
        success: function(data) {
            centers = data;
            $(".centersel").each(function() {
                $(this).html("");
                $(this).append("<option value=''>All</option>");
                for (i = 0; i<centers.length; i++) {
                    $(this).append("<option value='"+centers[i]+"'>"+centers[i]+"</option>");
                }
            });
        },
        error: function() {
            showerr("Error loading cost centers!");
        }
    });
    $.ajax({
        type: "POST",
        url: apiurl,
        data: { "action": "gettags" },
        success: function(data) {
            tags = data;
            tags.sort();
            $("#tagslist").html("");
            for (t in tags)
                $("#tagslist").append("<li>"+tags[t]+"</li>");
            $("#tagslist").selectable({
                selected: function(event, ui) {
                    if (editedfields.indexOf("tags") == -1)
                        editedfields.push("tags");
                },
                unselected: function(event, ui) {
                    if (editedfields.indexOf("tags") == -1)
                        editedfields.push("tags");
                }
            });
            $("#tagslist li").addClass("ui-widget-content");
        }
    });

    // Every minute, make sure session is still good.  Logout if bad.
    if (!sessioncheckinterval)
        sessioncheckinterval = setInterval(checksession, 60000);
}

// Clear everything, then check if we have a good session.
function clearpage() {
    $("#login").hide();
    $("#transactions").hide();
    $("#transactiondetail").dialog("close");
    $("#accounts").hide();
    $("#errormsg").hide();
    $("#searchoptions").hide();
    $("#newaccount").hide();
    $("#tagselect").hide();
    $("#linktransactions").hide();
    $("#reports").hide();
    $("#reports #summary").hide();
    $("#reports #close").hide();
    $("#reports #reopen").hide();
    $("#username").val("");
    $("#password").val("");
    if (sessioncheckinterval) {
        clearInterval(sessioncheckinterval);
        sessioncheckinterval = null;
    }

    $.ajax({
        type: "POST",
        url: apiurl,
        data: { "action": "checklogin" },
        success: function(data) {
            if (data) {
                loginsuccess();
            } else {
                $("#login").show();
                $("#login").center();
                $("#username").focus();
            }
        },
        error: function() {
            $("#login").show();
            $("#login").center();
            $("#username").focus();
        }
    });
}

// Clear page if our session is bad.
function checksession() {
    $.ajax({
        type: "POST",
        url: apiurl,
        data: { "action": "checklogin" },
        success: function(data) {
            if (data) {
            } else {
                clearpage();
            }
        },
        error: function() {
            clearpage();
        }
    });
}

function addCommas(number) {
    x = number.toString().split('.');
    x1 = x[0];
    x2 = x.length > 1 ? '.' + x[1] : '';
    var rgx = /(\d+)(\d{3})/;
    while (rgx.test(x1)) {
        x1 = x1.replace(rgx, '$1' + ',' + '$2');
    }
    return x1 + x2;
}

function dollarstr(amount) {
    return "$"+addCommas(Math.abs(amount/100).toFixed(2));
}

// Convert amount in positive/negative cents to human-readable format
function decoratedollar() {
    if ($(this).text().substring(0,1) == "$")
        return;
    amount = parseInt($(this).text());
    if (amount > 0)
        $(this).addClass("posnum");
    else
        $(this).removeClass("posnum");
    $(this).text(dollarstr(amount));
}

// Get accounts and balances, load up table and search options
function loadaccounts() {
    $.ajax({
        type: "POST",
        url: apiurl,
        data: { "action": "accounts" },
        success: function(data) {
            var olddate = new Date();
            olddate.setDate(olddate.getDate()-7);
            accountsearches = accountsearches.slice(0,1);
            $("#accounts > #bankaccounts").html("");
            for (i in data) {
                if (data[i]["subaccounts"].length == 0)
                    data[i]["subaccounts"] = [{"name":"", "date": "", "amount": "0"}]
                for (j in data[i]["subaccounts"]) {
                    newaccount = "<div class='account useraccount' id='account"+accountsearches.length+"'>";
                    newaccount += "<span class='accountname'>"+data[i]["name"]+"</span> / ";
                    newaccount += "<span class='subname'>"+data[i]["subaccounts"][j]["name"]+"</span>";
                    newaccount += "<div class='dollar accountbalance'>"+data[i]["subaccounts"][j]["amount"]+"</div>";
                    newaccount += "<div class='accountupdate'>"+data[i]["subaccounts"][j]["date"]+"</div>";
                    newaccount += "</div>";
                    $("#accounts > #bankaccounts").append(newaccount);
                    var acctdate = new Date(data[i]["subaccounts"][j]["date"]);
                    if (acctdate < olddate)
                        $("#accounts account"+accountsearches.length).addClass("ui-state-error");
                    accountsearches.push({"account":data[i]["name"], "subaccount": data[i]["subaccounts"][j]["name"]});
                }
            }
            $(".dollar").each(decoratedollar);
            $(".account").click(function() {
                skip = 0;
                query = accountsearches[parseInt($(this).attr("id").substring(7))];
                $(".account").removeClass("ui-state-active");
                $(this).addClass("ui-state-active");
                loadtransactions();
            });
            $("#accounts").show();
            $("#account0").addClass("ui-state-active");
            query = accountsearches[0];
            loadtransactions();
        },
        error: function() {
            showerror("Error loading accounts");
        }
    });
}

// Store our saved fields for this transaction
function savetransaction() {
    if (editedfields.length > 0) {
        updatejson = new Object();
        for (f in editedfields) {
            newval = $("#transactiondetail #"+editedfields[f]).val();
            if (newval == "")
                newval = $("#transactiondetail #"+editedfields[f]).text();
            updatejson[editedfields[f]] = newval;
        }
        if (editedfields.indexOf("amount") != -1) {
            newamount = $("#transactiondetail #amount").text().replace("$","").replace(",","");
            if (newamount.indexOf(".") == -1) {
                newamount += ".00";
            } else if (newamount.indexOf(".") != (newamount.length-3)) {
                showerror("Bad amount");
                return;
            }
            newamount = newamount.replace(".","");
            if (showtrans["amount"] > 0)
                updatejson["amount"] = parseInt(newamount);
            else
                updatejson["amount"] = -parseInt(newamount);
        }
        if (editedfields.indexOf("tags") != -1) {
            updatejson["tags"] = showtrans["tags"];
        }
        $.ajax({
            type: "POST",
            url: apiurl,
            data: { "action": "updatetransaction", "id": showtrans["id"], "data" : JSON.stringify(updatejson) },
            success: function(data) {
                if (data) {
                    showtransaction(showing);
                    loadtransactions();
                } else {
                    showerror("Error saving transaction");
                }
            },
            error: function() {
                showerror("HTTP Error saving transaction");
            }
        });
    }
}

// Show transaction detail, either index of loadedtransactions array, or object of a transaction.
function showtransaction(t) {
    if (typeof(t) == "number") {
        if (showing == t) {
            $("#transactiondetail").dialog("close");
            showing = -1;
            return;
        }
        showing = t;
        showtrans = loadedtransactions[t];
    } else {
        showtrans = t;
    }
    editedfields = [];
    $("#transactiondetail #save").button("disable");
    if (showtrans["state"] == "open")
        $("#transactiondetail #saveclose").button("enable");
    else
        $("#transactiondetail #saveclose").button("disable");
    $("#transactiondetail > #file").hide();
    $("#transactiondetail .transdata").each(function () {
        name = $(this).attr("id");
        $(this).text("");
        if (showtrans[name] != undefined)
            $(this).text(showtrans[name]);
    });
    $("#transactiondetail .transdataval").each(function () {
        name = $(this).attr("id");
        $(this).val("");
        if (showtrans[name] != undefined)
            $(this).val(showtrans[name]);
    });
    $("#transactiondetail > #attr").html("");
    for (key in showtrans) {
        if ((key.indexOf("attr_") == 0) && (showtrans[key] != "")) {
            $("#transactiondetail > #attr").append(key.substr(5) + ": " + showtrans[key] + "<br>");
        }
    }
    if (showtrans["file"] != undefined) {
        $("#transactiondetail > #file").attr("src",apiurl+"?image="+showtrans["id"]);
        $("#transactiondetail > #file").show();
    }
    $(".dollar").each(decoratedollar);
    if (categories[showtrans["category"]] != undefined)
        $("#transactiondetail #subcategory").autocomplete("option", "source", categories[showtrans["category"]]);
    else
        $("#transactiondetail #subcategory").autocomplete("option", "source", allcategories);
    $("#transactiondetail #linked").html("");
    if (showtrans["parents"] != undefined) {
        $("#transactiondetail #linked").append("Linked Transactions:<br>");
        for (i=0; i<showtrans["parents"].length; i++)
            $("#transactiondetail #linked").append("<a href='#' class='translink'>"+showtrans["parents"][i]+"</a><br>");
    }
    if (showtrans["children"] != undefined) {
        if ($("#transactiondetail #linked").html() == "")
            $("#transactiondetail #linked").append("Linked Transactions:<br>");
        for (i=0; i<showtrans["children"].length; i++)
            $("#transactiondetail #linked").append("<a href='#' class='translink'>"+showtrans["children"][i]+"</a><br>");
    }
    $("#transactiondetail #tags").html("");
    if (showtrans["tags"] != undefined) {
        for (var tag in showtrans["tags"])
            $("#transactiondetail #tags").append(showtrans["tags"][tag] + " ");
    }
    $(".translink").click(function (event) {
        event.preventDefault();
        $.ajax({
            type: "POST",
            url: apiurl,
            data: { "action": "search", "query": JSON.stringify({"id": "$eq:" + $(this).text()}) },
            success: function(data) {
                if (data && data.length) {
                    showtransaction(data[0]);
                } else {
                    showerror("Bad transaction data");
                }
            },
            error: function(data) {
                showerror("Error getting transaction");
            }
        });
    });
    $("#transactiondetail").dialog("open");
}

// Search, load transactions to main table
function loadtransactions() {
    // hack to duplicate the existing query
    transquery = JSON.parse(JSON.stringify(query))
    for (i=0; i<$("#searchoptions .queryoption").length; i++) {
        if ($("#searchoptions .queryoption").eq(i).val())
            transquery[$("#searchoptions .queryoption").eq(i).attr("id")] = $("#searchoptions .queryoption").eq(i).val()
    }
    postdata = { "action": "search", "limit": limit, "skip": skip, "query": JSON.stringify(transquery) }
    for (i=0; i<$("#searchoptions .searchoption").length; i++) {
        if ($("#searchoptions .searchoption").eq(i).val() != "")
            postdata[$("#searchoptions .searchoption").eq(i).attr("id")] = $("#searchoptions .searchoption").eq(i).val()
    }
    $.ajax({
        type: "POST",
        url: apiurl,
        data: postdata,
        success: function(data) {
            total = 0;
            orig_total = 0;
            loadedtransactions = data;
            $("#showlimit").text(skip);
            $("#showmax").text(skip+data.length);
            for (t=0; t<data.length; t++) {
                if ($("#transtablebody > #trans"+t).length == 0) {
                    $("#transtablebody").append("<tr class='transaction' id='trans"+t+"'>"+
                        "<td class='date'></td>"+
                        "<td class='description'></td>"+
                        "<td class='category'></td>"+
                        "<td class='centertd'></td>"+
                        "<td class='dollar'></td>"+
                        "<td><button class='close'>Close</button></tr>");
                    $("#trans"+t).click(function() {
                        showtransaction(parseInt($(this).attr("id").substring(5)));
                    });
                    $("#trans"+t+" .close").button();
                    $("#trans"+t+" .close").click(function() {
                        transid = parseInt($(this).parent().parent().attr("id").substring(5));
                        $.ajax({
                            type: "POST",
                            url: apiurl,
                            data: { "action": "updatetransaction", "id": loadedtransactions[transid]["id"], "data" : JSON.stringify({"state": "closed"}) },
                            context: this,
                            success: function(data) {
                                if (data) {
                                    $(this).button("disable");
                                    if (($("#searchoptions #state").val() != "") && ($("#searchoptions #state").val() != "closed"))
                                        $(this).parent().parent().slideUp(200);
                                } else
                                    showerror("Error closing transaction");
                            },
                            error: function(data) {
                                showerror("HTTP error closing transaction");
                            }
                        });
                        return false;
                    });
                }
                $("#transtablebody > #trans"+t+" .date").text(data[t]["date"]);
                $("#transtablebody > #trans"+t+" .description").text(data[t]["desc"]);
                $("#transtablebody > #trans"+t+" .dollar").text(data[t]["amount"]);
                $("#transtablebody > #trans"+t+" .centertd").text(data[t]["center"]);
                $("#transtablebody > #trans"+t+" .category").text("");
                if (data[t]["subcategory"])
                    $("#transtablebody > #trans"+t+" .category").text(data[t]["subcategory"]);
                else if (data[t]["category"])
                    $("#transtablebody > #trans"+t+" .category").text(data[t]["category"]);
                if (data[t]["state"] != "closed")
                    $("#trans"+t+" .close").button("enable");
                else
                    $("#trans"+t+" .close").button("disable");
                $("#transtablebody > #trans"+t).show();
                total += data[t]["amount"];
                orig_total += data[t]["orig_amount"];
            }
            for (t=data.length; $("#transtablebody > #trans"+t).length > 0; t++)
                $("#transtablebody > #trans"+t).remove();
            $("#transactionsum").text(total);
            $("#transactionorig").text(orig_total);
            $(".dollar").each(decoratedollar);
            $("#transtablebody td").addClass("ui-widget-content");
            $("#transtablebody td").removeClass("ui-state-hover");
            $("#transtablebody button").removeClass("ui-state-hover");
            $("#transtablebody tr").hover(
                function() {
                    $(this).children("td").addClass("ui-state-hover");
                },
                function() {
                    $(this).children("td").removeClass("ui-state-hover");
                }
            );
            $("#transtablebody tr").draggable({
                revert: true,
                helper: "clone"
            });
            $("#transactions").show();
            $("#transtable").width($("#searchoptions").offset().left-$("#transtable").offset().left-5);
            $("html, body").animate({ scrollTop: 0 }, 0);
        },
        error: function() {
            showerror("Transaction loading error");
        }
    });
}

function clearlink() {
    linkparent = "";
    linkchildren = [];
    $("#linktransactions div").html("");
    $("#reports").css("top", $("#linktransactions").offset().top+$("#linktransactions").height()+10)
}

function getpiedata(data, months) {
    var subdata = [];
    var colors = Highcharts.getOptions().colors;
    for (var i in data) {
        data[i].y = data[i].amount;
        data[i].color = colors[i];
        for (j in data[i]["subs"]) {
            subdata.push({
                name: data[i]["subs"][j]["name"],
                y: (data[i]["subs"][j]["amount"]/months),
                color: Highcharts.Color(colors[i]).brighten(0.2).get(),
                startdate: data[i].startdate,
                enddate: data[i].enddate
            });
        }
    }
    return [ {
        data: data,
        dataLabels: {
            formatter: function() {
                return this.y/total > .05 ? this.point.name : null;
            },
            distance: 50,
            connectorWidth: 0
        },
        size: '60%',
        cursor: 'pointer',
        events: {
            click: function(event) {
                $("#searchoptions #category").val(event.point.name);
                $("#searchoptions #subcategory").val("");
                if ($("#searchoptions #startdate").val() == "")
                    $("#searchoptions #startdate").val(event.point.startdate)
                if ($("#searchoptions #enddate").val() == "")
                    $("#searchoptions #enddate").val(event.point.enddate)
                loadtransactions();
                $("#reports #close").click();
            }
        }
    }, {
        data: subdata,
        dataLabels: {
            enabled: false
        },
        innerSize: '60%',
        cursor: 'pointer',
        events: {
            click: function(event) {
                $("#searchoptions #category").val("");
                $("#searchoptions #subcategory").val(event.point.name);
                if ($("#searchoptions #startdate").val() == "")
                    $("#searchoptions #startdate").val(event.point.startdate)
                if ($("#searchoptions #enddate").val() == "")
                    $("#searchoptions #enddate").val(event.point.enddate)
                loadtransactions();
                $("#reports #close").click();
            }
        }
    } ]
}

function gettrendsettings(data, months) {
    var monthnames = [];
    var series = [];
    for (i in data) {
        for (j in data[i]["subs"])
            if (monthnames.indexOf(data[i]["subs"][j]["name"]) == -1)
                monthnames.push(data[i]["subs"][j]["name"]);
    }
    monthnames.sort();
    for (i in data) {
        data[i].data = [];
        for (j in monthnames)
            data[i].data.push(0);
        for (j in data[i]["subs"])
            data[i].data[monthnames.indexOf(data[i]["subs"][j]["name"])] = data[i]["subs"][j]["amount"];
    }
    return {
        series: data,
        plotOptions: {
            column: {
                stacking: 'normal',
                events: {
                    click: function(event) {
                        $("#searchoptions #category").val(this.name);
                        $("#searchoptions #subcategory").val("");
                        $("#searchoptions #startdate").val(event.point.series.data[event.point.x].category + "-01")
                        $("#searchoptions #enddate").val(event.point.series.data[event.point.x].category + "-31")
                        loadtransactions();
                        $("#reports #close").click();
                    }
                }
            },
        },
        xAxis: {
            categories: monthnames
        },
        yAxis: {
            stackLabels: {
                enabled: true,
                style: {
                    fontWeight: 'bold'
                },
                formatter: function() {
                    return (this.total<0?"-":"") + dollarstr(this.total);
                }
            },
            title: {
                text: null
            },
            labels: {
                formatter: function() {
                    return (this.total<0?"-":"") + dollarstr(this.value);
                }
            }
        },
        tooltip: {
            formatter: function() {
                return this.series.name +': '+ (this.y<0?"-":"") + dollarstr(this.y);
            }
        },
        legend: {
            enabled: false
        }
    };
}

$(document).ready(function () {
    $('[contenteditable]').live('focus', function() {
        var $this = $(this);
        $this.data('before', $this.text());
            return $this;
    }).live('blur keyup paste', function() {
        var $this = $(this);
        if ($this.data('before') !== $this.text()) {
            $this.data('before', $this.text());
            if (editedfields.indexOf($(this).attr("id")) == -1) {
                editedfields.push($(this).attr("id"));
                $("#transactiondetail .savebutton").button("enable");
            }
        }
        return $this;
    });

    $("#transactiondetail .savebutton").button();
    $("#transactiondetail #save").click(savetransaction);
    $("#transactiondetail #saveclose").click(function() {
        $("#transactiondetail #state").val("closed")
        editedfields.push("state");
        savetransaction();
    });
    $("#transactiondetail > #dateselect").datepicker({
        dateFormat: "yy-mm-dd",
        altField: "#transactiondetail > #date",
        onSelect: function(dateText, inst) {
            $("#transactiondetail > #date").text(dateText);
            if (editedfields.indexOf("date") == -1) {
                editedfields.push("date");
                $("#transactiondetail .savebutton").button("enable");
            }
        }
    });
    $("#transactiondetail > #date").click(function() {
        $("#transactiondetail > #dateselect").datepicker("show");
    });
    $("#transactiondetail select,input").change(function () {
        if (editedfields.indexOf($(this).attr("id")) == -1) {
            editedfields.push($(this).attr("id"));
            $("#transactiondetail .savebutton").button("enable");
        }
        if (($(this).attr("id") == "state") && ($(this).val() != "closed"))
            $("#transactiondetail #saveclose").button("disable");
    });
    $("#transactiondetail #addtag").button({
        icons: {
            primary: "ui-icon-circle-plus"
        },
        text: false
    });
    $("#transactiondetail #addtag").click(function () {
        $("#tagselect").show();
        $("#tagselect").center();
        $("#tagselect ol").removeClass("ui-selected");
        if (showtrans["tags"] != undefined)
            $("#tagselect ol").each(function () {
                if (showtrans["tags"].indexOf($(this).text()) != -1)
                    $(this).addClass("ui-selected");
            });
    });
    $("#tagselect button").button();
    $("#tagselect button").click(function () {
        showtrans["tags"] = [];
        $("#transactiondetail #tags").html("");
        $("#tagselect ol .ui-selected").each(function () {
            showtrans["tags"].push($(this).text());
            $("#transactiondetail #tags").append($(this).text() + " ");
            if (editedfields.indexOf("tags") == -1)
                editedfields.push("tags");
            $("#transactiondetail .savebutton").button("enable");
        });
        $("#tagselect").hide();
    });
    $("#transactiondetail").dialog({
        modal: true,
        autoOpen: false,
        title: "Edit Transaction",
        minWidth: 600,
        close: function() {
            showing = -1;
        }
    });

    $("#searchoptions .date").datepicker({
        dateFormat: "yy-mm-dd",
        onClose: function(dateText, inst) {
            loadtransactions();
        }
    });
  
    $("#searchoptions #center").change(function() {
        loadtransactions();
    });
  
    $("#searchoptions #executesearch").button();
    $("#searchoptions #executesearch").click(function () {
        skip = 0;
        loadtransactions();
    });
  
    $("#searchoptions #clearsearch").button();
    $("#searchoptions #clearsearch").click(function () {
        $("#searchoptions .searchoption").each(function () { $(this).val(""); });
        $("#searchoptions .queryoption").each(function () { $(this).val(""); });
        loadtransactions();
    });

    $("#errormsg").dialog({
        modal: true,
        autoOpen: false,
        title: "Error",
        minWidth: 250,
        buttons: {
            Ok: function() {
                $(this).dialog("close");
            }
        }
    });

    $(".limit").click(function(event) {
        event.preventDefault();
        if ($(this).text() == "all")
            limit = Number.MAX_VALUE;
        else
            limit = parseInt($(this).text());
        loadtransactions();
    });
  
    $(".page").click(function(event) {
        event.preventDefault();
        if ($(this).html() == "&lt;&lt;") {
            if (skip == 0)
                return;
            skip -= limit;
            if (skip < 0)
                skip = 0;
            loadtransactions();
        } else {
            if (loadedtransactions.length < limit)
                return;
            skip += limit;
            loadtransactions();
        }
    });

    $("#logout").click(function(event) {
        event.preventDefault();
        $.ajax({
            type: "POST",
            url: apiurl,
            data: { "action": "logout" },
            success: function() {
                clearpage();
            },
            error: function() {
                clearpage();
            }
        });
    });

    $("#loginsubmit").click(function () {
        $("#loginform").submit();
    });

    $("#loginform").keypress(function (e) {
        if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
            $("#loginform").submit();
            return false;
        } else {
            return true;
        }
    });

    $("#loginform").submit(function () {
        $.ajax({
            type: "POST",
            url: apiurl,
            data: { "action": "login", "username": $("#username").val(), "password": $("#password").val() },
            success: function(data) {
                if (data) {
                    loginsuccess();
                } else {
                    showerror("Login Failed");
                }
            },
            error: function() {
                showerror("Login Error");
            }
        });
    });

    $("#newuser").click(function () {
        $.ajax({
            type: "POST",
            url: apiurl,
            data: { "action": "newuser", "username": $("#username").val(), "password": $("#password").val() },
            success: function(data) {
                if (data) {
                    $("#loginsubmit").click();
                } else {
                    showerror("Username already exists");
                }
            },
            error: function() {
                showerror("Error making new user");
            }
        });
    });

    $("#newaccount").dialog({
        modal: true,
        autoOpen: false,
        title: "Add/Edit Account"
    });

    $("#addaccount").click(function (event) {
        event.preventDefault();
        $.ajax({
            type: "POST",
            url: apiurl,
            data: { "action": "getbanks" },
            success: function(data) {
                newhtml = "<option value=''>Select a bank</option>";
                for (i=0; i<data.length; i++)
                    newhtml += "<option value='"+data[i]+"'>"+data[i]+"</option>";
                $("#newaccount #bankname").html(newhtml);
            }
        });
        $("#newaccount > #createaccount").button("disable");
        $("#newaccount input").each(function() {
            $(this).val("");
        });
        $("#newaccount").dialog("open");
    });
  
    $("#newaccount .required").keyup(function () {
        ready = true;
        for (var i=0; i<$("#newaccount .required").length; i++) {
            if ($("#newaccount .required").eq(i).val() == "")
                ready = false;
        }
        if (ready)
            $("#newaccount > #createaccount").button("enable");
    });
  
    $("#newaccount > #createaccount").button();
    $("#newaccount > #createaccount").click(function () {
        account = {}
        $("#newaccount input,select").each(function() {
            if ($(this).val() != "")
                account[$(this).attr("id")] = $(this).val();
        });
        $.ajax({
            type: "POST",
            url: apiurl,
            data: { "action": "editaccount", "account": JSON.stringify(account) },
            success: function(data) {
                if (data) {
                    $("#newaccount").dialog("close");
                    loadaccounts();
                } else {
                    showerror("Could not add/edit account");
                }
            },
            error: function() {
                showerror("HTTP Error editing account");
            }
        });
    });

    $("#linktransactions div").droppable({
        drop: function (event, ui) {
            var t = parseInt($(ui.draggable).attr("id").substring(5));
            if ($(this).attr("id") == "parent") {
                $(this).html("");
                linkparent = loadedtransactions[t]["id"];
            } else {
                linkchildren.push(loadedtransactions[t]["id"])
            }
            $(this).append(loadedtransactions[t]["date"] + " " + (loadedtransactions[t]["amount"]<0?"-":"") + dollarstr(loadedtransactions[t]["amount"]) + " " + loadedtransactions[t]["desc"] + "<br>");
            $("#reports").css("top", $("#linktransactions").offset().top+$("#linktransactions").height()+10)
        },
        tolerance: "touch",
        hoverClass: "ui-state-active"
    });
    $("#linktransactions button").button();
    $("#linktransactions #clear").click(clearlink);
    $("#linktransactions #combine,#split,#dup").click(function () {
        $.ajax({
            type: "POST",
            url: apiurl,
            data: { "action": "link",
                "parent": linkparent,
                "children": JSON.stringify(linkchildren),
                "linktype": $(this).attr("id")
            },
            success: function(data) {
                if (data) {
                    clearlink();
                    loadtransactions();
                } else {
                    showerror("Error linking transactions");
                }
            },
            error: function() {
                showerror("HTTP error linking transactions");
            }
        });
    });

    $(".download").click(function (e) {
        e.preventDefault();
        transquery = JSON.parse(JSON.stringify(query))
        for (i=0; i<$("#searchoptions .queryoption").length; i++) {
            if ($("#searchoptions .queryoption").eq(i).val())
                transquery[$("#searchoptions .queryoption").eq(i).attr("id")] = $("#searchoptions .queryoption").eq(i).val()
        }
        postdata = { "action": "search", "limit": limit, "skip": skip, "query": JSON.stringify(transquery) }
        for (i=0; i<$("#searchoptions .searchoption").length; i++) {
            if ($("#searchoptions .searchoption").eq(i).val() != "")
                postdata[$("#searchoptions .searchoption").eq(i).attr("id")] = $("#searchoptions .searchoption").eq(i).val()
        }
        postdata["format"] = $(this).text();
        document.location = apiurl + "?" + $.param(postdata);
    });

    $(".doreport").click(function (e) {
        e.preventDefault();
        if ($(this).attr("id") != "reopen") {
            reportid = $(this).attr("id");
            curreport = -1;
        }
        $("#reports").animate({
            top: "0px",
            left: "0px",
            height: $(document).height(),
            width: "100%",
            margin: "5px"
        }, 400, function() {
            $("#reports #close").show();
            $("#reports #summary").show();
            $("#reports #reportgraph").show();
            $("#reports #reopen").show();
            $("#reports .doreport").hide();
            if (curreport == reportid)
                return;
            curreport = reportid;
            filteropts = JSON.parse(JSON.stringify(reportopts[curreport]["filter"]));
            $("#searchoptions .queryoption").each(function() {
                if ($(this).val() != "")
                    filteropts[$(this).attr("id")] = $(this).val();
            });
            $("#reports #summary").html("");
            if (chart != null)
                chart.destroy();
            $.ajax({
                type: "POST",
                url: apiurl,
                data: {"action": "summary",
                    "startdate": $("#searchoptions #startdate").val() || reportopts[curreport]["defstart"],
                    "enddate": $("#searchoptions #enddate").val() || reportopts[curreport]["defend"],
                    "filter": JSON.stringify(filteropts),
                    "filterout": JSON.stringify(reportopts[curreport]["filterout"]),
                    "key": reportopts[curreport]["key"],
                    "keydef": reportopts[curreport]["keydef"],
                    "keysort": reportopts[curreport]["keysort"],
                    "keysortrev": reportopts[curreport]["keysortrev"],
                    "subkey": reportopts[curreport]["subkey"],
                    "subkeydef": reportopts[curreport]["subkeydef"],
                    "subkeysort": reportopts[curreport]["subkeysort"],
                    "subkeysortrev": reportopts[curreport]["subkeysortrev"],
                    "modify": reportopts[curreport]["modify"] || "",
                },
                success: function(data) {
                    if (data.length == 0)
                        return;
                    var months = parseInt(data[0]["enddate"].substr(6,2)) - parseInt(data[0]["startdate"].substr(6,2)) + 1;
                    var total = 0;
                    for (i in data) {
                        keyhtml = "<div class='summaryline'>"+data[i]["name"]+" <span class='dollar'>"+(data[i]["amount"]/months)+"</span></div>";
                        keyhtml += "<div class='detail'>"
                        for (j in data[i]["subs"]) {
                            keyhtml += data[i]["subs"][j]["name"] + " <span class='dollar'>" + (data[i]["subs"][j]["amount"]/months) + "</span><br>";
                        }
                        keyhtml += "</div>"
                        $("#reports #summary").append(keyhtml);
                        total += data[i]["amount"];
                    }
                    $("#reports #summary").append("<b>Total: <span class='dollar'>"+(total/months)+"</span></b>");
                    $("#reports #summary .detail").hide();
                    $("#reports #summary .dollar").each(decoratedollar);
                    $("#reports #summary .summaryline").click(function () {
                        if ($(this).next().is(":hidden"))
                            $(this).next().slideDown();
                        else
                            $(this).next().slideUp();
                    });
                    if (typeof Highcharts != "undefined") {
                        $("#reports #reportgraph").height($(window).height());
                        var subdata = [];
                        var colors = Highcharts.getOptions().colors;
                        for (var i in data) {
                            data[i].y = data[i].amount;
                            data[i].color = colors[i];
                            for (j in data[i]["subs"]) {
                                subdata.push({
                                    name: data[i]["subs"][j]["name"],
                                    y: (data[i]["subs"][j]["amount"]/months),
                                    color: Highcharts.Color(colors[i]).brighten(0.2).get()
                                });
                            }
                        }
                        var chartsettings = {
                            chart: {
                                renderTo: 'reportgraph',
                                type: reportopts[curreport]["type"]
                            },
                            title: {
                                text: reportopts[curreport]["title"]
                            },
                            subtitle: {
                                text: data[0]["startdate"] + ' to ' + data[0]["enddate"] +
                                    ', Total: ' + dollarstr(total) +
                                    ((months>1)?', Average: ' + dollarstr(total/months):'')
                            },
                            tooltip: {
                                formatter: function() {
                                    return '<b>'+ this.point.name +'</b>: '+ dollarstr(this.y);
                                }
                            },
                            plotOptions: {
                                shadow: false,
                            },
                            series: reportopts[curreport].getseries(data, months),
                        }
                        $.extend(chartsettings, reportopts[curreport].getsettings(data, months))
                        chart = new Highcharts.Chart(chartsettings);
                    }
                },
                error: function() {
                    showerror("HTTP error getting summary");
                }
            });
        });
    });

    $("#reports #close").click(function (e) {
        e.preventDefault();
        $("#reports #summary").hide();
        $("#reports #reportgraph").hide()
        $("#reports #close").hide();
        $("#reports .doreport").show();
        $("#reports").animate({
            top: $("#linktransactions").offset().top+$("#linktransactions").height()+10,
            left: $("#linktransactions").offset().left,
            height: 0,
            width: $("#searchoptions").width(),
            margin: "0px"
        });
    });

    clearpage();
  
    $("body").addClass("ui-widget");

    $("th").addClass("ui-state-default");

});

jQuery.fn.center = function () {
    this.css("position","absolute");
    this.css("top", (($(window).height() - this.outerHeight()) / 2) +
        $(window).scrollTop() + "px");
    this.css("left", (($(window).width() - this.outerWidth()) / 2) +
        $(window).scrollLeft() + "px");
    return this;
}
