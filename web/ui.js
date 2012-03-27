apiurl = "api.py";
loadedtransactions = [];
showing = -1;
editedfields = []

function loginsuccess() {
  $("#login").hide();
  $("#bottomlinks").show();
  loadaccounts();
  loadtransactions();
}

function clearpage() {
  $("#login").show();
  $("#transactions").hide();
  $("#transactiondetail").hide();
  $("#accounts").hide();
  $("#bottomlinks").hide();

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
          $("#accountstablebody").append("<tr><td>"+data[i]["name"]+"</td><td>"+data[i]["subaccounts"][j]["name"]+"</td><td class='dollar'>"+data[i]["subaccounts"][j]["amount"]+"</td><td>"+data[i]["subaccounts"][j]["date"]+"</td></tr>");
        }
      }
      $(".dollar").each(decoratedollar);
      $("#accounts").show();
    },
    error: function() {
      alert("Error loading accounts");
    }
  });
}

function savetransaction() {
  if (editedfields.length > 0) {
    //alert("Save " + editedfields.join() + " for " + loadedtransactions[showing]["id"]);
    updatejson = new Object();
    for (f in editedfields)
      updatejson[editedfields[f]] = $("#transactiondetail > #"+editedfields[f]).text();
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "updatetransaction", "id": loadedtransactions[showing]["id"], "data" : JSON.stringify(updatejson) },
      success: function(data) {
        if (data) {
          showtransaction(showing);
          loadtransactions();
        } else {
          alert("Error saving transaction");
        }
      },
      error: function() {
        alert("HTTP Error saving transaction");
      }
    });
  }
}

function showtransaction(t) {
  if (showing == t) {
    $("#transactiondetail").hide();
    showing = -1;
    return;
  }
  showing = t;
  editedfields = [];
  $("#transactiondetail > #file").hide();
  $("#transactiondetail > div").each(function () {
    name = $(this).attr("id");
    $("#transactiondetail > #"+name).text();
    if (loadedtransactions[t][name] != undefined)
      $("#transactiondetail > #"+name).text(loadedtransactions[t][name]);
  });
  if (loadedtransactions[t]["file"] != undefined) {
    $("#transactiondetail > #file").attr("src",apiurl+"?image="+loadedtransactions[t]["id"]);
    $("#transactiondetail > #file").show();
  }
  $(".dollar").each(decoratedollar);
  $("#transactiondetail").show();
}

function loadtransactions() {
  $("#transtablebody").html("");
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "search", "limit": 25, "query": JSON.stringify({"amount": "$ne:0" }) },
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
      alert("Transaction loading error");
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
      if (editedfields.indexOf($(this).attr("id")) == -1)
        editedfields.push($(this).attr("id"));
    }
    return $this;
  });

  $("#transactiondetail > #save").click(savetransaction);
  $("#transactiondetail > #dateselect").datepicker({
    dateFormat: "yy-mm-dd",
    altField: "#transactiondetail > #date",
    onSelect: function(dateText, inst) {
      $("#transactiondetail > #date").text(dateText);
      if (editedfields.indexOf("date") == -1)
        editedfields.push("date");
    }
  });
  $("#transactiondetail > #date").click(function() {
    $("#transactiondetail > #dateselect").datepicker("show");
  });

  $("#logout").click(function(event) {
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
          alert("Login Failed");
        }
      },
      error: function() {
        alert("Login Error");
      }
    });
  });

  clearpage();

});
