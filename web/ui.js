var apiurl = "api.py";
var loadedtransactions = [];
var accountsearches = [ {"status": "$ne:closed" }, {"amount": "$ne:0"}, {} ];
var showing = -1;
var editedfields = []
var limit = 25;
var skip = 0;
var query = accountsearches[0];
var sessioncheckinterval = null;

function showerror(err) {
  $("#errormsg").text(err);
  $("#errormsg").dialog("open");
}

function loginsuccess() {
  $("#login").hide();
  $("#bottomlinks").show();
  $("#searchoptions").show();
  loadedtransactions = [];
  accountsearches = accountsearches.slice(0,3);
  showing = -1;
  limit = 25;
  skip = 0;
  $("#accounts > .useraccount").remove();
  loadaccounts();
  loadtransactions();

  if (!sessioncheckinterval)
    sessioncheckinterval = setInterval(checksession, 60000);
}

function clearpage() {
  $("#login").hide();
  $("#transactions").hide();
  $("#transactiondetail").dialog("close");
  $("#accounts").hide();
  $("#bottomlinks").hide();
  $("#errormsg").hide();
  $("#searchoptions").hide();
  $("#newaccount").hide();
  $("#username").val("");
  $("#password").val("");
  if (sessioncheckinterval)
    clearInterval(sessioncheckinterval);

  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "checklogin" },
    success: function(data) {
      if (data) {
        loginsuccess();
      } else {
        $("#login").show();
      }
    },
    error: function() {
      $("#login").show();
    }
  });
}

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

function decoratedollar() {
  if ($(this).text().substring(0,1) == "$")
    return;
  amount = parseInt($(this).text());
  if (amount > 0)
    $(this).addClass("posnum");
  $(this).text("$"+Math.abs(amount/100).toFixed(2));
}

function loadaccounts() {
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "accounts" },
    success: function(data) {
      for (i in data) {
        for (j in data[i]["subaccounts"]) {
          newaccount = "<div class='account useraccount'>";
          newaccount += "<div class='accountname'>"+data[i]["name"]+"</div>";
          newaccount += "<div class='subname'>"+data[i]["subaccounts"][j]["name"]+"</div>";
          newaccount += "<div class='dollar accountbalance'>"+data[i]["subaccounts"][j]["amount"]+"</div>";
          newaccount += "<div class='accountupdate'>"+data[i]["subaccounts"][j]["date"]+"</div>";
          newaccount += "</div>";
          $("#accounts").append(newaccount);
          accountsearches.push({"account":data[i]["name"], "subaccount": data[i]["subaccounts"][j]["name"]});
        }
      }
      $(".dollar").each(decoratedollar);
      $(".account").click(function() {
        for (i=0; i < $(this).parent().children(".account").length; i++) {
          if ($(this).text() == $(this).parent().children(".account").eq(i).text()) {
            query = accountsearches[i];
            loadtransactions();
            return;
          }
        }
      });
      $("#accounts").show();
    },
    error: function() {
      showerror("Error loading accounts");
    }
  });
}

function savetransaction() {
  if (editedfields.length > 0) {
    updatejson = new Object();
    for (f in editedfields)
      updatejson[editedfields[f]] = $("#transactiondetail > #"+editedfields[f]).text();
    if (editedfields.indexOf("amount") != -1) {
      newamount = $("#transactiondetail > #amount").text().replace("$","").replace(",","");
      if (newamount.indexOf(".") == -1) {
        newamount += ".00";
      } else if (newamount.indexOf(".") != (newamount.length-3)) {
        showerror("Bad amount");
        return;
      }
      newamount = newamount.replace(".","");
      if (loadedtransactions[showing]["amount"] > 0)
        updatejson["amount"] = parseInt(newamount);
      else
        updatejson["amount"] = -parseInt(newamount);
    }
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "updatetransaction", "id": loadedtransactions[showing]["id"], "data" : JSON.stringify(updatejson) },
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

function showtransaction(t) {
  if (showing == t) {
    $("#transactiondetail").dialog("close");
    showing = -1;
    return;
  }
  showing = t;
  editedfields = [];
  $("#transactiondetail > #save").hide();
  $("#transactiondetail > #file").hide();
  $("#transactiondetail .transdata").each(function () {
    name = $(this).attr("id");
    $(this).text();
    if (loadedtransactions[t][name] != undefined)
      $(this).text(loadedtransactions[t][name]);
  });
  $("#transactiondetail > #attr").html();
  for (key in loadedtransactions[t]) {
    if (key.indexOf("attr_") == 0) {
      $("#transactiondetail > #attr").append(key.substr(5) + ": " + loadedtransactions[t][key] + "<br>");
    }
  }
  if (loadedtransactions[t]["file"] != undefined) {
    $("#transactiondetail > #file").attr("src",apiurl+"?image="+loadedtransactions[t]["id"]);
    $("#transactiondetail > #file").show();
  }
  $(".dollar").each(decoratedollar);
  $("#transactiondetail").dialog("open");
}

function loadtransactions() {
  $("#transtablebody").html("");
  $.ajax({
    type: "POST",
    url: apiurl,
    data: {
      "action": "search",
      "limit": limit,
      "skip": skip,
      "startdate": $("#startdate").val(),
      "enddate": $("#enddate").val(),
      "query": JSON.stringify(query)
    },
    success: function(data) {
      total = 0;
      loadedtransactions = data;
      for (t=0; t<data.length; t++) {
        $("#transtablebody").append("<tr class='transaction' id='trans"+t+"'><td class='date'>"+data[t]["date"]+"</td><td class='description'>"+data[t]["desc"]+"</td><td class='dollar'>"+data[t]["amount"]+"</td></tr>\n");
        total += data[t]["amount"];
      }
      $("#transactionsum").text(total);
      $(".dollar").each(decoratedollar);
      $(".transaction").click(function() {
        showtransaction(parseInt($(this).attr("id").substring(5)));
      });
      $("#transactions").show();
    },
    error: function() {
      showerror("Transaction loading error");
    }
  });
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
        $("#transactiondetail > #save").show();
      }
    }
    return $this;
  });

  $("#transactiondetail > #save").click(savetransaction);
  $("#transactiondetail > #dateselect").datepicker({
    dateFormat: "yy-mm-dd",
    altField: "#transactiondetail > #date",
    onSelect: function(dateText, inst) {
      $("#transactiondetail > #date").text(dateText);
      if (editedfields.indexOf("date") == -1) {
        editedfields.push("date");
        $("#transactiondetail > #save").show();
      }
    }
  });
  $("#transactiondetail > #date").click(function() {
    $("#transactiondetail > #dateselect").datepicker("show");
  });
  $("#transactiondetail").dialog({
    modal: true,
    autoOpen: false,
    title: "Edit Transaction",
    minWidth: 600
  });

  $("#searchoptions .date").datepicker({
    dateFormat: "yy-mm-dd",
    onClose: function(dateText, inst) {
      loadtransactions();
    }
  });

  $("#errormsg").dialog({
    modal: true,
    autoOpen: false,
    title: "Error",
    minWidth: 250
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

  clearpage();

});
