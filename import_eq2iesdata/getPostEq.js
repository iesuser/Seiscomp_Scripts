function OnLoad(eqOriginTime) //'2010-12-17 12:48:31'
{

	if(errorStationList != '') window.location = '../error/error.php?link='+encodeURI("window.location='../eq/eq_list.php'")+'&text='+errorStationList+' სადგური(ები) არ არის ბაზაში რეგისტრირებული';

	if(errorStationList == '') {
		GetSameEqsXml(eqOriginTime);
		document.getElementById('eqLabel').style.display = 'none';
		document.getElementById('sameEqTable').style.display = 'none';
		document.getElementById('samePrimariesTable').style.display = 'none';
		document.getElementById('eqPrimarybuttons').style.display = 'none';
	}
}



//მნიშვნელობა გადაყავს float ტიპში 

function ParseFloat(value)

{

	value = value.replace(/ /g,"");

	if (value == '') return '';

	else return parseFloat(value);

}



//ინდექსირებული მასივის ელემენდების დამთვლელი

function AssociativeArrayLength(array)

{

	var length = 0;

	for (var object in array){

		length++;

	}

	return length;


}



function AjaxRequest(url,paramStr,async,cfunc)

{	

	xmlhttp = getHTTPObject();

	if (this.xmlhttp == null) return false;

	if(async) xmlhttp.onreadystatechange=cfunc;

	xmlhttp.open("POST",url,async);

	xmlhttp.setRequestHeader("Content-Type", "application/x-www-form-urlencoded"); 

	xmlhttp.send(encodeURI(paramStr));

	if(!async) cfunc();

}





function getHTTPObject()

{

   if (window.ActiveXObject) 

       return new ActiveXObject("Microsoft.XMLHTTP");

   else if (window.XMLHttpRequest) 

       return new XMLHttpRequest();

   else {

      alert("Your browser does not support AJAX.");

      return null;

   }

}



//სტრინგი გადაყავს დროში

function ConvertStringToDatetime(dateTime) //fomati : 2010-11-18 14:19:03.089

{

	var yyyy = dateTime.substring(0,4);

	var mm = dateTime.substring(5,7);

	var dd = dateTime.substring(8,10);

	var HH = dateTime.substring(11,13);

	var MM = dateTime.substring(14,16);

	var ss = dateTime.substring(17,19);

	var msec = dateTime.substring(20,dateTime.length);

	return new Date(yyyy, parseInt(mm)-1, dd, HH, MM, ss, msec);

}



// ავსებს sameEqsTable ცხრილს იმ მიწისძვრებით რომელიც პოსტით გადმოცემულ მიწისძვრასთან არის ახლოს დროის მიხედვით

function GetSameEqsXml(eqOriginTime)

{

	var paramStr = 'GetSameEqsXml=1';



	if(eqOriginTime.replace(/ /g,"") != '')

		paramStr += '&eqOriginTime=' + eqOriginTime;

	else paramStr += '&eqOriginTime=' + getFirstWaveTime();

	

	var sameEqsTable = document.getElementById('sameEqsTable');

	sameEqsTable.rows[2].cells[0].innerHTML = '';

	sameEqsTable.rows[2].cells[1].innerHTML = document.getElementById('eqOriginTime').value;

	sameEqsTable.rows[2].cells[2].innerHTML = ParseFloat(document.getElementById('eqLatitude').value);

	sameEqsTable.rows[2].cells[3].innerHTML = ParseFloat(document.getElementById('eqLongitude').value);

	if(typeof postEq['magnitudes']['ml'] != 'undefined')		

		sameEqsTable.rows[2].cells[4].innerHTML = postEq['magnitudes']['ml']['value'];

	sameEqsTable.rows[2].cells[5].innerHTML = document.getElementById('eqStationRecordCount').value;

	sameEqsTable.rows[2].cells[6].innerHTML = document.getElementById('eqRegionGe').value;

	sameEqsTable.rows[2].cells[7].innerHTML = document.getElementById('eqTimeHypocenterProgram').value;


	AjaxRequest("getEqXmls.php",paramStr,false,function()

	{

		if (xmlhttp.readyState == 4 && xmlhttp.status == 200)

		{


			xmlDoc=xmlhttp.responseXML;


			eqs=xmlDoc.getElementsByTagName("EQ");

			var row;

			if(eqs.length == 0) 

			{

				document.getElementById('ajaxLoader').style.display = 'block';

				saveEqAndPrimaries();

			}else document.getElementById('ajaxLoader').style.display = 'none';

			for (i=0;i<eqs.length;i++)

			{

				//alert('dsad');

				id = eqs[i].getElementsByTagName("id")[0].firstChild.nodeValue;

				

				row = sameEqsTable.insertRow(sameEqsTable.rows.length);

				row.insertCell(0).innerHTML = '<a href="newEdit_eq.php?id='+id+'" target="_blank"><img src="../images/eq/view.gif" align="absmiddle" border="0"/></a>';

				row.insertCell(1).innerHTML = eqs[i].getElementsByTagName("originTime")[0].firstChild.nodeValue;

				row.insertCell(2).innerHTML = eqs[i].getElementsByTagName("latitude")[0].firstChild.nodeValue;

				row.insertCell(3).innerHTML = eqs[i].getElementsByTagName("longitude")[0].firstChild.nodeValue;

				row.insertCell(4).innerHTML = eqs[i].getElementsByTagName("ml")[0].firstChild.nodeValue; 

				row.insertCell(5).innerHTML = eqs[i].getElementsByTagName("stationRecordCount")[0].firstChild.nodeValue;

				row.insertCell(6).innerHTML = eqs[i].getElementsByTagName("region")[0].firstChild.nodeValue;

				row.insertCell(7).innerHTML = eqs[i].getElementsByTagName("timeHypocenterProgram")[0].firstChild.nodeValue;

				row.cells[0].style.width = '35px';

				row.cells[4].style.width = '35px';

				row.setAttribute("class", "sameEqsTd");

				for(k=1; k<row.cells.length;k++)

					row.cells[k].setAttribute("onclick", "javascript:checkEqRewrites("+id+");");

			}

		}

	});

}



//კითხულობს მიწისძვრის(შესაბამისი id-ით) ინფორმაციას XML ით ajax ის გამოყენებით და ავსებს შესაბამის ცხრილს

function GetSameEqXml(id)

{

	var paramStr = 'GetSameEqXml=1&id='+id;

	var sameEqTable = document.getElementById('sameEqTable');

	sameEqTable.rows[2].cells[1].innerHTML = document.getElementById('eqOriginTime').value;

	sameEqTable.rows[2].cells[2].innerHTML = ParseFloat(document.getElementById('eqLatitude').value);

	sameEqTable.rows[2].cells[3].innerHTML = ParseFloat(document.getElementById('eqLongitude').value);

	sameEqTable.rows[2].cells[4].innerHTML = document.getElementById('eqDepth').value;

	sameEqTable.rows[2].cells[5].innerHTML = document.getElementById('soft').value;

	sameEqTable.rows[2].cells[6].innerHTML = document.getElementById('eqStationRecordCount').value;

	sameEqTable.rows[2].cells[7].innerHTML = document.getElementById('eqStationUsedCount').value;

	sameEqTable.rows[2].cells[8].innerHTML = document.getElementById('eqGap').value;

	sameEqTable.rows[2].cells[9].innerHTML = postEq['stationMinDistance'];

	if(typeof postEq['magnitudes']['ml'] != 'undefined'){
		sameEqTable.rows[2].cells[10].innerHTML = postEq['magnitudes']['ml']['value'];
		sameEqTable.rows[2].cells[11].innerHTML = postEq['magnitudes']['ml']['uncertainty'];
	}

	sameEqTable.rows[2].cells[12].innerHTML = document.getElementById('eqRegionGe').value;


	AjaxRequest("getEqXmls.php",paramStr,false,function()

	{

		if (xmlhttp.readyState == 4 && xmlhttp.status == 200){

			xmlDoc=xmlhttp.responseXML;

			eq=xmlDoc.getElementsByTagName("EQ");



			var row = sameEqTable.rows[4];

			row.cells[0].innerHTML = '<a href="newEdit_eq.php?id='+id+'" target="_blank"><img src="../images/eq/view.gif" align="absmiddle" border="0"/></a>';

			row.cells[1].innerHTML = eq[0].getElementsByTagName("originTime")[0].firstChild.nodeValue;

			row.cells[2].innerHTML = eq[0].getElementsByTagName("latitude")[0].firstChild.nodeValue;

			row.cells[3].innerHTML = eq[0].getElementsByTagName("longitude")[0].firstChild.nodeValue;

			row.cells[4].innerHTML = eq[0].getElementsByTagName("depth")[0].firstChild.nodeValue;

			row.cells[5].innerHTML = eq[0].getElementsByTagName("timeHypocenterProgram")[0].firstChild.nodeValue;

			row.cells[6].innerHTML = eq[0].getElementsByTagName("stationRecordCount")[0].firstChild.nodeValue;

			row.cells[7].innerHTML = eq[0].getElementsByTagName("stationUsedCount")[0].firstChild.nodeValue;

			row.cells[8].innerHTML = eq[0].getElementsByTagName("gap")[0].firstChild.nodeValue;

			row.cells[9].innerHTML = eq[0].getElementsByTagName("stationMinDistance")[0].firstChild.nodeValue;

			row.cells[10].innerHTML = eq[0].getElementsByTagName("ml")[0].firstChild.nodeValue;

			row.cells[11].innerHTML = eq[0].getElementsByTagName("mlUncertainty")[0].firstChild.nodeValue;

			row.cells[12].innerHTML = eq[0].getElementsByTagName("region")[0].firstChild.nodeValue; 

			

		}

	});

}



//ამოწმებს ბაზაში არის თუ არა მიწისძვრისთვის დამატებული პირველადი 

function checkIfEqPrimaryIssetsInDatabase(id, primary_code, networkCode, locationCode)

{

	var reslt = false;

	var paramStr = 'checkIfStationIssetsInDatabase=1&id='+id+"&primary_code="+primary_code+"&networkCode="+networkCode+"&locationCode="+locationCode;

	AjaxRequest("getEqXmls.php",paramStr,false,function()

	{

		if (xmlhttp.readyState == 4 && xmlhttp.status == 200)

		{

						

			xmlDoc=xmlhttp.responseXML;

			var isset = xmlDoc.getElementsByTagName("isset")[0].firstChild.nodeValue;

			if(isset=='true') reslt = true;

		}

	});

	return reslt;

}



//კითხულობს მიწისძვრის(შესაბამისი id-ით) პირველადებს XML ით ajax ის გამოყენებით და ავსებს შესაბამის ცხრილს

function GetPrimariesXmlFromDatabase(id)

{

	var paramStr = 'GetPrimariesXmlFromDatabase=1&id='+id;

	var waveNameLength = AssociativeArrayLength(postWaveNames);

	for(waveName in postWaveNames)

		paramStr += '&'+waveName+'=1';

	console.log(paramStr)

	AjaxRequest("getEqXmls.php",paramStr,false,function()

	{

		if (xmlhttp.readyState == 4 && xmlhttp.status == 200)

		{

			

			var samePrimariesTable = document.getElementById('samePrimariesTable');

			//alert(xmlhttp.responseText)

			xmlDoc=xmlhttp.responseXML;

			prs=xmlDoc.getElementsByTagName("PR");

			var row;

			if(prs.length == 0)

			{

				row = samePrimariesTable.insertRow(samePrimariesTable.rows.length);

				row.insertCell(0).innerHTML = "არცერთი პირველადი არ არის დამატებული";

				row.cells[0].colSpan = "12";

				row.cells[0].style.height = '35px';

			}

			else

				for (i=0;i<prs.length;i++)

				{

					id = prs[i].getElementsByTagName("id")[0].firstChild.nodeValue;

					

					row = samePrimariesTable.insertRow(samePrimariesTable.rows.length);

					

					var code = prs[i].getElementsByTagName("stationCode")[0].firstChild.nodeValue;

					row.insertCell(row.cells.length).innerHTML = "";

					row.insertCell(row.cells.length).innerHTML = code;

					row.insertCell(row.cells.length).innerHTML = prs[i].getElementsByTagName("networkCode")[0].firstChild.nodeValue;

					row.insertCell(row.cells.length).innerHTML = prs[i].getElementsByTagName("locationCode")[0].firstChild.nodeValue; 

					
					console.log(prs[i]);

					for(j = 0; j < AssociativeArrayLength(postWaveNames); j++)

					{

						waveName = samePrimariesTable.rows[1].cells[4+j].id;

						if(typeof prs[i].getElementsByTagName(waveName+"Time")[0] != 'undefined')

							row.insertCell(row.cells.length).innerHTML	= prs[i].getElementsByTagName(waveName+"Time")[0].firstChild.nodeValue;

						else row.insertCell(row.cells.length).innerHTML = '';

					}

					

					row.insertCell(row.cells.length).innerHTML = prs[i].getElementsByTagName("rezOriginTimeP")[0].firstChild.nodeValue;

					row.insertCell(row.cells.length).innerHTML = prs[i].getElementsByTagName("rezOriginTimeS")[0].firstChild.nodeValue;

					row.insertCell(row.cells.length).innerHTML = prs[i].getElementsByTagName("hypocenterDistance")[0].firstChild.nodeValue;

					row.insertCell(row.cells.length).innerHTML = prs[i].getElementsByTagName("eqCalculated")[0].firstChild.nodeValue;



					if(i < prs.length - 1)

						for(k = 0; k < row.cells.length; k++)	row.cells[k].style.borderBottom = '1px solid #CCC';

					row.cells[1].style.borderLeft = '1px solid #CCC';

					row.cells[4].style.borderLeft = '1px solid #CCC';

					for(k = 4+waveNameLength; k < row.cells.length; k++)	row.cells[k].style.borderLeft = '1px solid #CCC';

					row.className = 'samePrimariesTabletr';

					if(checkIfEqPrimaryIssetsInPostData(code)) row.style.color = 'rgb(255, 0, 51)';

				}

		}

	});

}



//ამოწმებს გადმოწცემული არის თუ არა პირველადი პოსტით დაა ბრუნებს შესაბამის მნიშვნელობას (true ,false)

function checkIfEqPrimaryIssetsInPostData(code)

{

	code = code.replace(/ /g,"");

	if(typeof primaries[code] != 'undefined') return true

	return false;

}



function insertSamePrimariesTableLabel(rowIndex)

{

	var samePrimariesTable = document.getElementById('samePrimariesTable');

	if(typeof samePrimariesTable.rows[rowIndex] == 'undefined')

		samePrimariesTable.insertRow(rowIndex);

	var row = samePrimariesTable.rows[rowIndex]; 

	row.insertCell(row.cells.length).innerHTML = 'მონიშვნა';

	row.insertCell(row.cells.length).innerHTML = 'სადგურის<br/>კოდი';

	row.insertCell(row.cells.length).innerHTML = 'ქსელის<br/>კოდი';

	row.insertCell(row.cells.length).innerHTML = 'ლოკალური<br/>კოდი';

		

	for(waveName in postWaveNames)

	{

		row.insertCell(row.cells.length).innerHTML = waveName;

		row.cells[row.cells.length-1].id = waveName;

	}

	

	row.insertCell(row.cells.length).innerHTML = 'გარბენის<br/>დრო (p)';

	row.insertCell(row.cells.length).innerHTML = 'გარბენის<br/>დრო (s)';

	row.insertCell(row.cells.length).innerHTML = 'ჰიპოცენტრული<br/>მანძილი';

	row.insertCell(row.cells.length).innerHTML = 'გამოთვლა';

	

	row.cells[0].style.borderBottom = '1px solid #CCC';

	for(i = 1; i < row.cells.length; i++)

		row.cells[i].className = 'wavesLabel';

	row.className = 'wavesLabels';

}



function createSamePrimariesTableHeader()

{

	insertSamePrimariesTableLabel(1);

	insertSamePrimariesTableLabel(document.getElementById('samePrimariesTableDatabaseHeader').rowIndex+1);

	document.getElementById('samePrimariesTablePostHeader').cells[0].colSpan = 8 + AssociativeArrayLength(postWaveNames);

	document.getElementById('samePrimariesTableDatabaseHeader').cells[0].colSpan = 8 + AssociativeArrayLength(postWaveNames);

}

	

//ავსებს samePrimariesTable ცხრილს პოსტ მონაცემებიდან

function FillSamePrimariesTable(id){

	cleanSamePrimariesTable();

	createSamePrimariesTableHeader()

	var i,STnum;

	var samePrimariesTable = document.getElementById('samePrimariesTable');

	

	var insertIndex = 2;	

	var waveNameLength = AssociativeArrayLength(postWaveNames);

	var i = 0;

	for (code in primaries)

	{

		STnum = 'ST'+i;

		row = samePrimariesTable.insertRow(insertIndex);

		row.insertCell(0).innerHTML = "<input id='newSt"+code+"Checkbox' type='checkbox' onChange='onCheckboxCheck(this)'/>";

		row.insertCell(1).innerHTML =  code;

		row.insertCell(2).innerHTML =  primaries[code]['networkCode'];

		row.insertCell(3).innerHTML =  primaries[code]['locationCode'];

		for(j = 0; j < waveNameLength; j++){

			if(typeof primaries[code]['waves'][samePrimariesTable.rows[1].cells[4+j].id] != 'undefined')
				row.insertCell(4+j).innerHTML = primaries[code]['waves'][samePrimariesTable.rows[1].cells[4+j].id]['time'];
			else row.insertCell(4+j).innerHTML = '';
			row.cells[4+j].width = '80px';

		}



		row.insertCell(row.cells.length).innerHTML =  primaries[code]['rezOriginTimeP'];
		row.insertCell(row.cells.length).innerHTML =  primaries[code]['rezOriginTimeS'];
		row.insertCell(row.cells.length).innerHTML =  primaries[code]['hypocenterDistance'];
		row.insertCell(row.cells.length).innerHTML =  primaries[code]['usedForCalculation'];

		if(i < stCount - 1)

			for(k = 0; k < row.cells.length; k++)	row.cells[k].style.borderBottom = '1px solid #CCC';

		row.cells[1].style.borderLeft = '1px solid #CCC';

		row.cells[4].style.borderLeft = '1px solid #CCC';

		for(k = 4+waveNameLength; k < row.cells.length; k++)	row.cells[k].style.borderLeft = '1px solid #CCC';

		row.className = 'samePrimariesTabletr';

		insertIndex++;

		if(checkIfEqPrimaryIssetsInDatabase(id, code, primaries[code]['networkCode'], primaries[code]['locationCode']))

			row.style.color = 'rgb(255, 0, 51)';

		else 

		{

			document.getElementById('newSt'+code+'Checkbox').checked = true;

			row.style.backgroundColor  = 'rgb(255,255,204)';

		}

		i++;

	}

}



//გადადის კონკრეტული მიწისძვრაზე, ამოწმებს პირველადებს არის თუ არა ბაზაში შეყვანილი

function checkEqRewrites(id)

{

	document.getElementById('sameEqsLabel').style.display = 'none';

	document.getElementById('sameEqsTable').style.display = 'none';

	document.getElementById('eqsButtons').style.display = 'none';

	document.getElementById('eqLabel').style.display = '';

	document.getElementById('sameEqTable').style.display = '';

	document.getElementById('samePrimariesTable').style.display = '';

	document.getElementById('eqPrimarybuttons').style.display = '';

	eq_id = id;

	GetSameEqXml(id);

	FillSamePrimariesTable(id);

	GetPrimariesXmlFromDatabase(id);

}



//ნიშნავს ყველა პირველადს და მიწისძვრის Checkbox -ებს გადასაწერად

function checkAll()

{

	document.getElementById('eqCheckbox').checked = mustCkeck;

	if(mustCkeck)

		document.getElementById('sameEqTable').rows[2].style.backgroundColor  = 'rgb(255,255,204)';

	else document.getElementById('sameEqTable').rows[2].style.backgroundColor  = 'rgb(255,255,255)';

	for(code in primaries)

	{

		document.getElementById('newSt'+code+'Checkbox').checked = mustCkeck;

		if(mustCkeck)

			document.getElementById('newSt'+code+'Checkbox').parentNode.parentNode.style.backgroundColor  = 'rgb(255,255,204)';

		else document.getElementById('newSt'+code+'Checkbox').parentNode.parentNode.style.backgroundColor  = 'rgb(255,255,255)';

	}

	if(mustCkeck) mustCkeck = false;

	else mustCkeck = true;

}



//კონკრეტული მიწისძვრის პირველადებიდან გამოდის უკან გადასაწერი მიწისძვრების ასარჩევ გვერდზე

function Back()

{

	document.getElementById('sameEqsLabel').style.display = 'block';

	document.getElementById('sameEqsTable').style.display = 'table';

	document.getElementById('eqsButtons').style.display = 'block';

	document.getElementById('eqLabel').style.display = 'none';

	document.getElementById('sameEqTable').style.display = 'none';

	document.getElementById('samePrimariesTable').style.display = 'none';

	document.getElementById('eqPrimarybuttons').style.display = 'none';

}



//წმინდავს samePrimariesTable ცხრილს

function cleanSamePrimariesTable()

{

	var samePrimariesHtml='';

	samePrimariesHtml+='          <tr class="wavesNamePandS" id="samePrimariesTablePostHeader">';

    samePrimariesHtml+='            <td colspan="12">დასამატებელი პირველადების მონაცემები</td>';

    samePrimariesHtml+='          </tr>';

    samePrimariesHtml+='          <tr></tr>';

    samePrimariesHtml+='          <tr class="wavesNamePandS" id="samePrimariesTableDatabaseHeader">';

    samePrimariesHtml+='            <td colspan="12">ბაზაში არსებული პირველადების მონაცემები</td>';

    samePrimariesHtml+='          </tr>';

	

	var samePrimariesTable = document.getElementById('samePrimariesTable');	

	samePrimariesTable.innerHTML = samePrimariesHtml;

	

}



//აბრუნებს მიწისძვრის დასამახსოვრებელ პარამეტრებს

function GetEqSaveParamsStr(){

	var paramStr = 'saveEq=1';
	paramStr += '&eqId=' + eq_id;

	if(document.getElementById('eqOriginTime').value.replace(/ /g,"") != '')
		paramStr += '&originTime=' + document.getElementById('eqOriginTime').value;
	else paramStr += '&originTime=' + getFirstWaveTime()
	

	paramStr += '&latitude=' + ParseFloat(document.getElementById('eqLatitude').value);
	paramStr += '&longitude=' + ParseFloat(document.getElementById('eqLongitude').value);
	paramStr += '&depth=' + document.getElementById('eqDepth').value;

	if(document.getElementById('eqOriginTime').value.replace(/ /g,"") != '') 
		paramStr += '&timeHypocenterProgram=' + document.getElementById('eqTimeHypocenterProgram').value;
	else paramStr += '&timeHypocenterProgram=Raw';

	var eqMagnitudeLength = 0;
	for(magnitudeType in postEq['magnitudes']){
		paramStr += '&eqMagnitudeType'+eqMagnitudeLength+'=' + magnitudeType;
		paramStr += '&eqMagnitude'+magnitudeType+'Value=' + postEq['magnitudes'][magnitudeType]['value'];
		paramStr += '&eqMagnitude'+magnitudeType+'minValue=' + postEq['magnitudes'][magnitudeType]['minValue'];
		paramStr += '&eqMagnitude'+magnitudeType+'maxValue=' + postEq['magnitudes'][magnitudeType]['maxValue'];
		paramStr += '&eqMagnitude'+magnitudeType+'Uncertainty=' + postEq['magnitudes'][magnitudeType]['uncertainty'];
		paramStr += '&eqMagnitude'+magnitudeType+'StationCount=' + postEq['magnitudes'][magnitudeType]['stationCount'];
		eqMagnitudeLength++;
	}

	paramStr += '&eqMagnitudeLength=' + eqMagnitudeLength;
	paramStr += '&shakeSource=' + document.getElementById('eqShakeSource').value;
	paramStr += '&area=' + document.getElementById('eqArea').value;
	paramStr += '&region_ge=' + document.getElementById('eqRegionGe').value;
	paramStr += '&region_en=' + document.getElementById('eqRegionEn').value;


	paramStr += '&eqInfoGe=' + document.getElementById('eqInfoGe').value;
	paramStr += '&eqInfoEn=' + document.getElementById('eqInfoEn').value;




	paramStr += '&intencity=' + document.getElementById('eqIntencity').value;
	
	//სადგურები
	paramStr += '&stationRecordCount=' + document.getElementById('eqStationRecordCount').value;
	paramStr += '&stationUsedCount=' + document.getElementById('eqStationUsedCount').value;
	paramStr += '&phasesCount=' + document.getElementById('eqPhasesCount').value;
	//paramStr += '&phasesUsedCount=' + document.getElementById('eqPhasesUsedCount').value;
	paramStr += '&gap=' + document.getElementById('eqGap').value;
	paramStr += '&stationMinDistance=' + postEq['stationMinDistance'];

	//ცდომილებები
	paramStr += '&timeUncertainty=' + document.getElementById('eqTimeUncertainty').value;
	paramStr += '&epicenterUncertainty=' + document.getElementById('eqHorizontalUncertainty').value;
	paramStr += '&latitudeUncertainty=' + document.getElementById('eqLatitudeUncertainty').value;
	paramStr += '&longitudeUncertainty=' + document.getElementById('eqLongitudeUncertainty').value;
	paramStr += '&depthUncertainty=' + document.getElementById('eqDepthUncertainty').value;
	
	paramStr += '&comment=' + document.getElementById('eqComment').value;

	paramStr += '&important=' + document.getElementById('eqImportant').value;
	paramStr += '&eqVmid=' + document.getElementById('eqVmId').value;


	return paramStr;

}



function getStationMinDistance()

{

	var minDistance = 'none';

	var distance = 0.0;

	for(code in primaries)

	{

		distance = ParseFloat(primaries[code]['hypocenterDistance'])

		if(distance != '')

		{

			minDistance = distance;

			break;

		}

	}

	if(minDistance != 'none')

		for(code in primaries)

		{

			distance = ParseFloat(primaries[code]['hypocenterDistance']);

			if(distance != '' && distance < minDistance)

				minDistance = distance;

		}

	else return '';

	return minDistance;

}



//ამატებს ბაზაში მიწისძვრას და შემდეგ პირველადებს

function saveEqAndPrimaries()

{

	eq_id = -1;

	AjaxRequest("insertUpdateDeleteEq.php",GetEqSaveParamsStr(),false,function()

	{

		if(xmlhttp.readyState == 4 && xmlhttp.status == 200)

		{

			

 			var response = xmlhttp.responseText;

			if (response.substring(response.length-9) == "eqUpdated" && response.length < 25)

			{

				eq_id = response.substring(0, response.length-10);

				SaveAllPrimaries(false);

			}else alert("Error: saveEqAndPrimaries Eq \n response: " + response);

		}

	});

}





//ქმნის პირველადის დასამახსოვრებელ სტრინგს პოსტით გადმოცემული მონაცემებიდან

function GetPrimarySaveParamStr(code)

{

	var paramStr = 'eqId= ' + eq_id;

	paramStr += '&savePrimary=true';

	

	//კოდი

	paramStr += "&networkCode="+primaries[code]['networkCode'];

	paramStr += "&stationCode=" + code;

	paramStr += "&locationCode="+primaries[code]['locationCode'];



	paramStr += '&waveLength=' + AssociativeArrayLength(primaries[code]['waves']);

	

	var i = 0;

	for(waveType in primaries[code]['waves'])

	{

		paramStr += '&waveType'+i+'=' + waveType;

		paramStr += '&wave'+waveType+'Time=' + primaries[code]['waves'][waveType]['time'];

		paramStr += '&wave'+waveType+'Quality=' + primaries[code]['waves'][waveType]['quality'];

		paramStr += '&wave'+waveType+'Weight=' + primaries[code]['waves'][waveType]['weight'];

		paramStr += '&wave'+waveType+'OnsetType=' + primaries[code]['waves'][waveType]['onsetType'];

		paramStr += '&wave'+waveType+'EqCalculated=' + primaries[code]['waves'][waveType]['usedForCalculation'];

		i++;

	}

	

	paramStr += '&magnitudeLength=' + AssociativeArrayLength(primaries[code]['magnitudes']);

	i = 0;

	for(magnitudeType in primaries[code]['magnitudes'])

	{

		paramStr += '&magnitudeType'+i+'=' + magnitudeType;

		paramStr += '&magnitude'+magnitudeType+'Value=' + primaries[code]['magnitudes'][magnitudeType]['value'];

		paramStr += '&magnitude'+magnitudeType+'Rezidual=' + primaries[code]['magnitudes'][magnitudeType]['residual'];

		i++;

	}

		

	

	paramStr += '&amplitudeLength=' + AssociativeArrayLength(primaries[code]['amplitudes']);

	

	i = 0;

	var j = 0;



	for(waveType in primaries[code]['amplitudes'])

	{

		paramStr += '&amplitudeType'+i+'=' + waveType;

		paramStr += '&amplitude'+i+'AxisLength=' + AssociativeArrayLength(primaries[code]['amplitudes'][waveType]);

		j=0;

		for(axisType in primaries[code]['amplitudes'][waveType])

		{

			paramStr += '&amplitude'+i+'AxisType'+j+'=' + axisType;

			paramStr += '&amplitude'+i+'Axis'+axisType+'Value=' + primaries[code]['amplitudes'][waveType][axisType]['value'];

			paramStr += '&amplitude'+i+'Axis'+axisType+'DominantPeriod=' + primaries[code]['amplitudes'][waveType][axisType]['dominantPeriod'];

			paramStr += '&amplitude'+i+'Axis'+axisType+'Time=' + primaries[code]['amplitudes'][waveType][axisType]['time'];

			paramStr += '&amplitude'+i+'Axis'+axisType+'Velocity=' + primaries[code]['amplitudes'][waveType][axisType]['velocity'];

			paramStr += '&amplitude'+i+'Axis'+axisType+'Program=' + primaries[code]['amplitudes'][waveType][axisType]['program'];

			j++;

		}

		i++;

	}



	paramStr += "&eSign=" + encodeURIComponent(primaries[code]['signE']);

	paramStr += "&nSign=" + encodeURIComponent(primaries[code]['signN']);

	paramStr += "&zSign=" + encodeURIComponent(primaries[code]['signZ']);

	

	paramStr += "&hypocenterDistance=" + primaries[code]['hypocenterDistance'];

	paramStr += "&azimute=" + primaries[code]['azimute'];

	paramStr += "&eqCalculated=" + primaries[code]['usedForCalculation'];

	paramStr += "&rezOriginTimeP=" + primaries[code]['rezOriginTimeP'];

	paramStr += "&rezOriginTimeS=" + primaries[code]['rezOriginTimeS'];

	paramStr += "&rezEpicentre=";



	return paramStr;

}



//ამახსოვრებს პირველადს

function savePrimary(code,async)

{

	if (eq_id == -1)

	{

		AddAndThenEditNewEqAndPrimaries();

	}

	else

	{

		AjaxRequest("insertUpdateDeletePrimary.php",GetPrimarySaveParamStr(code),async,function()

		{

			

			if(xmlhttp.readyState == 4 && xmlhttp.status == 200)

			{			

				if (xmlhttp.responseText == "primaryUpdated")

				{

					

				}else alert("Error: save " + code + '\n' + '|'+xmlhttp.responseText+'|');

			}

		});

	}

}



//ამახსოვრებს, ამატებს ბაზაში ყველა პირველადს (პოსტით გადმოცემულს)

function SaveAllPrimaries(async)

{	

	for(code in primaries)

	{

		savePrimary(code,async);

	}

	window.location = 'newEdit_eq.php?id='+eq_id;

}



//აბრუნებს პირველი ფაზის სახელს შესაბამისი სადგურიდან

function getFirstWaveName(stationCode)

{	

	var rWaveType = 'none';

	var time = 1000000000000000000000;

	for(var wavesType in primaries[stationCode]['waves'])

	{

		if(ConvertStringToDatetime(primaries[stationCode]['waves'][wavesType]['time']).getTime() < time)

		{

			time = ConvertStringToDatetime(primaries[stationCode]['waves'][wavesType]['time']).getTime();

			rWaveType = wavesType;

		}

	}

	return rWaveType;

}



//აბრუნებს პირველი ფაზის შემოსვლის დროს (ყველა სადგურიდან)

function getFirstWaveTime()

{	

	var rTime;

	var time = 1000000000000000000000;

	for(stationCode in primaries)

		for(var wavesType in primaries[stationCode]['waves'])

		{

			if(ConvertStringToDatetime(primaries[stationCode]['waves'][wavesType]['time']).getTime() < time )

			{

				time = ConvertStringToDatetime(primaries[stationCode]['waves'][wavesType]['time']).getTime();

				rTime = primaries[stationCode]['waves'][wavesType]['time'];

			}

		}

	return rTime;

}



//გადაყავს SHM-დან გამოგზავნილი ტალღის სახელი ბაზაში არსებული ფორმატში(დიდი და პატარა ასოების მიხედვით). ამოწმებს არსებობს თუ არა ასეთი ტალღა ბაზაში.

function convertWaveName(shmWaveName)

{

	if((shmWaveName == 's') || (shmWaveName == 'S') || (shmWaveName == 'p') || (shmWaveName == 'P'))

		return shmWaveName;

	for(waveName in waveNames)

	{

		if(shmWaveName.toLowerCase() == waveName.toLowerCase())

		return waveName;

	}

	return 'error';

}



//გადაყავს SHM-დან გამოგზავნილი მაგნიტუდის სახელი ბაზაში არსებული ფორმატში(დიდი და პატარა ასოების მიხედვით). ამოწმებს არსებობს თუ არა ასეთი მაგნიტუდა ბაზაში.

function convertMagName(shmMagName)

{

	for(magName in magNames)

	{

		if(shmMagName.toLowerCase() == magName.toLowerCase())

		return magName;

	}

	return 'error';

}



//ბაზაში არსებული პირველდების მონიშვნისას უცვლის ფერს შესაბამის row-ს

function onCheckboxCheck(checkbox)

{

	if(checkbox.checked)

		checkbox.parentNode.parentNode.style.backgroundColor  = 'rgb(255,255,204)';

	else 

		checkbox.parentNode.parentNode.style.backgroundColor  = 'rgb(255,255,255)';

}





//ანახლებს მიწისძვრას თაავისი პირველადებით. 

function updateEqAndPrimaries()

{

	if(document.getElementById('eqCheckbox').checked)

	{

		AjaxRequest("insertUpdateDeleteEq.php",GetEqSaveParamsStr(),false,function()

		{

			if(xmlhttp.readyState == 4 && xmlhttp.status == 200)

			{

				

				var response = xmlhttp.responseText;

				if (response.substring(response.length-9) == "eqUpdated" && response.length < 25)

				{

					eq_id = response.substring(0, response.length-10);

					updateallPrimaries(false);

				}else alert("Error: updateEqAndPrimaries Eq \n response: " + response);

			}

		});

	}else updateallPrimaries(false);

}



//ანახლებს მიწისძვრის ყველა პირველადს

function updateallPrimaries(async)

{	

	document.getElementById('ajaxLoader').style.display = 'block';

	for(code in primaries)

	{

		if(document.getElementById('newSt'+code+'Checkbox').checked)

		{

			if(checkIfEqPrimaryIssetsInDatabase(eq_id, code, primaries[code]['networkCode'], primaries[code]['locationCode']))

			{

				updatePrimary(code)

			}else 

			{

				savePrimary(code, false);

			}	

		}

	}

	window.location = 'newEdit_eq.php?id='+eq_id;

}



//პირველდის წაშლა და შემდგომ დამახსოვრება

function updatePrimary(code)

{	

	var paramStr = "eqId=" + eq_id;

	paramStr += "&dropPrimary=1";

	

	paramStr += "&stationCode=" + code;

	paramStr += "&networkCode=" + primaries[code]['networkCode'];

	paramStr += "&locationCode=" + primaries[code]['locationCode'];

	

	

	AjaxRequest("insertUpdateDeletePrimary.php", paramStr, false, function()

	{

		if (xmlhttp.readyState == 4 && xmlhttp.status == 200)

		{	

			if(xmlhttp.responseText == "primaryDeleted")

			{

				savePrimary(code, false);

			}else alert("Error: delete " + code + '\n' + xmlhttp.responseText);

		}

	});

}



function closePostEqWindow()

{

	if(!window.close())

		window.location = 'eq_list.php';

}