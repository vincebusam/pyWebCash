apiurl = "api.py";
loadedtransactions = [];
showing = -1;

function showtransaction(t) {
  if (showing == t) {
    $("#transactiondetail").hide();
    showing = -1;
    return;
  }
  showing = t;
  $("#transactiondetail").show();
  newhtml = "Transaction Detail<br>\n";
  newhtml += loadedtransactions[t]["desc"] + "<br>\n";
  if (loadedtransactions[t]["file"] != undefined) {
    newhtml += loadedtransactions[t]["file"] + "<br>\n";
    newhtml += "<img src='"+apiurl+"?image="+loadedtransactions[t]["id"]+"'><br>\n";
  }
  $("#transactiondetail").html(newhtml);
}

function loadtransactions() {
  $("#transtablebody").html("");
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "search", "limit": 25, "query": '{"amount": "$ne:0" }' },
    success: function(data) {
      total = 0;
      loadedtransactions = data;
      for (t=0; t<data.length; t++) {
        $("#transtablebody").append("<tr class='transaction' id='trans"+t+"'><td class='date'>"+data[t]["date"]+"</td><td class='description'>"+data[t]["desc"]+"</td><td class='dollar'>"+data[t]["amount"]+"</td></tr>\n");
        total += data[t]["amount"];
      }
      $("#transactionsum").html(total);
      $(".dollar").each(function() {
        amount = parseInt($(this).html());
        if (amount > 0)
          $(this).addClass("posnum");
        $(this).html("$"+Math.abs(amount/100).toFixed(2));
      });
      $(".transaction").click(function() {
        showtransaction(parseInt($(this).attr("id").substring(5)));
      });
    },
    error: function() {
      alert("Transaction loading error");
    }
  });
}

$(document).ready(function () {
  $("#login").hide();
  $("#transactions").hide();
  $("#transactiondetail").hide();

  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "checklogin" },
    success: function(data) {
      if (data) {
        $("#transactions").show();
        loadtransactions();
      } else {
        $("#login").show();
      }
    },
    error: function() {
      $("#login").show();
    }
  });

  $("#loginsubmit").click(function () {
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "login", "username": $("#username").val(), "password": $("#password").val() },
      success: function(data) {
        if (data) {
          $("#login").hide();
          $("#transactions").show();
          loadtransactions();
        } else {
          alert("Login Failed");
        }
      },
      error: function() {
        alert("Login Error");
      }
    });
  });

});
