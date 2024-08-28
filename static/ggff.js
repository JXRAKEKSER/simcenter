


			function go(){
			var x = new Date()
			var hours = x.getHours().toString()
			hours=hours.length==1 ? 0+hours : hours;

			var minutes=x.getMinutes().toString()
			minutes=minutes.length==1 ? 0+minutes : minutes;

			var seconds=x.getSeconds().toString()
			seconds=seconds.length==1 ? 0+seconds : seconds;

			var xl1= hours + ":" +  minutes + ":" +  seconds;
			var Myvar = pll + ":00";
			console.log(Myvar);
			console.log(xl1);
			if (Myvar == xl1) { 
			console.log("РАБОТАЕТ"); 			
			var synth = window.speechSynthesis;
    			message = new SpeechSynthesisUtterance();
    			message.rate=0.8;
    			message.text ='Пройдите в кабинет номер '+ kkl ;
    			synth.speak(message); 
    			speechSynthesis.getVoices();
			}

			}

			
			setInterval('go()',1000)


