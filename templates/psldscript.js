let btn = document.querySelector('button');

let text123 = document.querySelector('text1234');

function scan(obj){
    console.log('scan start')
    // form submission starts
    // button is disabled
    btn.classList.add('spin');
    btn.disabled = true;

    // This disables the whole form via the fieldset
    btn.form.firstElementChild.disabled = true;

    $.ajax({
        type: "GET",
            url: "http://127.0.0.1:8080",
            contentType: false,
            cache: false,
            processData: false,
            success: function(data){
                if (data == "") {
                    document.getElementById("error_text").innerHTML = '<b>Ошибка при сканировании. Попробуйте ещё раз</b>';
                    btn.classList.remove('spin');
                    btn.disabled = false;
                    btn.form.firstElementChild.disabled = false
                }else {
                    console.log(data);
                    if (data.slice(2,5) == "RUS"){
                        let series = data.slice(44, 47) + data[72] + data.slice(47, 54);
                        //location.href = "172.29.4.10:5000/reg/" + series;
                    }
                }
            }

    });
}