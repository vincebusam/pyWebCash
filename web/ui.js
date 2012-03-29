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
      $("#accounts > .useraccount").remove();
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
    $(this).text("");
    if (loadedtransactions[t][name] != undefined)
      $(this).text(loadedtransactions[t][name]);
  });
  $("#transactiondetail .transdataval").each(function () {
    name = $(this).attr("id");
    $(this).val("");
    if (loadedtransactions[t][name] != undefined)
      $(this).val(loadedtransactions[t][name]);
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
        if ($("#transtablebody > #trans"+t).length == 0) {
          $("#transtablebody").append("<tr class='transaction' id='trans"+t+"'><td class='date'></td><td class='description'></td><td class='dollar'></td></tr>");
          $("#trans"+t).click(function() {
            showtransaction(parseInt($(this).attr("id").substring(5)));
          });
        }
        $("#transtablebody > #trans"+t+" .date").text(data[t]["date"]);
        $("#transtablebody > #trans"+t+" .description").text(data[t]["desc"]);
        $("#transtablebody > #trans"+t+" .dollar").text(data[t]["amount"]);
        total += data[t]["amount"];
      }
      for (t=data.length; t<$("#transtablebody tr").length; t++)
        $("#transtablebody > #trans"+t).remove();
      $("#transactionsum").text(total);
      $(".dollar").each(decoratedollar);
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
        $("#newaccount #bank").html(newhtml);
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
    account = new Object();
    $("#newaccount input,select").each(function() {
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

  clearpage();

});
