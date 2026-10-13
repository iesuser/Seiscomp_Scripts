<?php
include("../block/globalVariables.php");
include("../block/db.php");
include("../block/functions.php");
// if(!HaveAccess("seismicData")){echo "test"; exit();}
if(!HaveAccess("seismicData")){echo CreatePageData($_POST," ../login.php"); exit();}
include("../block/language.php");
// aq unda shemocmdes uzers aqvs tu ara am miwisdzvris damatebis ufleba (drois mixedvit)				!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title><?php echo $page_title;?> | მიწისძვრები</title>
<link href="../block/style.css" rel="stylesheet" type="text/css"/>
<?php include("../block/formenu/formenu.php"); ?>
<script type='text/javascript' src='../js/functions.js'></script>
<script type='text/javascript' src='../block/datetimepicker/datetimepicker_css_Ge.js'></script>
<script type="text/javascript" src="../block/georgian_language.js"></script>
<script type='text/javascript' src='../js/mask.js'></script>
<script type='text/javascript' src='../js/popupForm.js'></script>
<script type='text/javascript' src='getPostEq.js'></script>
<script type="text/javascript">
var stCount = <?php echo $ST_number = (isset($_POST['ST_number']))? $_POST['ST_number']:0;?>;
var selectedEqId;
var operatorfullname = '<?php echo $_SESSION["fullname"];?>';
var eq_id;
var primaries = new Array();
var postWaveNames = new Array();
var waveNames = new Array();
var magNames = new Array();
var waveName;
var magName;

var postEq = new Array();
var mustCkeck = true;
var stName = '';

<?php
mysql_select_db($dbSite,$db);
$eqWaveTypes = mysql_query("SELECT name FROM eq_wave_types");
while($waveName = mysql_fetch_array($eqWaveTypes))
{
	?>
	waveNames['<?php echo $waveName['name']?>'] = true;
	<?php
}

$eqMagnitudeTypes = mysql_query("SELECT name FROM eq_magnitude_types");
while($magName = mysql_fetch_array($eqMagnitudeTypes))
{
	?>
	magNames['<?php echo $magName['name']?>'] = true;
	<?php
}

mysql_select_db($dbGeoData, $db);
$errorStationList = "";
$ST_number = (isset($_POST['ST_number']))? $_POST['ST_number']:0;
for ($i=0; $i < $ST_number; $i++)
{
	$STnum = "ST".$i."_";
	?>
	stName = '<?php echo $_POST[$STnum."name"]?>';
	<?php
	$stationCode = $_POST[$STnum."name"];

	$networkCode = $locationCode = $stationId = "";
	$waveTime = substr(SHMtimeToPhpPlusMsec($_POST[$STnum."wave0_time"]), 0, 19); //პირველადის პირველი ტალღის დრო, გვჭირდება სადგურის ID ის გასაგებად

	//თუ პოსტით მიღებული გვაქვს network_code და location_code (ეს ხდება როცა მიწისძვრა იმპორტდება import_eq.php ფაილიდან და არა SHM-დან)
	if(isset($_POST[$STnum."network_code"]) and isset($_POST[$STnum."location_code"])){
		$networkCode = $_POST[$STnum."network_code"];
		$locationCode = $_POST[$STnum."location_code"];
		//შევამოწმოთ ბაზაში თუ გვაქვს რეგისტრირებული შესაბამისი სადგური (ქსელის, ლოკალური კოდით და დროით)
		//პირველ რიგში შევამოწმოთ თუ არის ალტერნატიული კოდით დარეგისტრირებული
		$sql = "SELECT station_id FROM stations_details 
				WHERE alternative_code = '$stationCode' AND network_code = '$networkCode' AND location_code = '$locationCode' AND (
					(instalation_date  = '0000-00-00 00:00:00' AND removing_date  = '0000-00-00 00:00:00') OR 
					(instalation_date != '0000-00-00 00:00:00' AND removing_date  = '0000-00-00 00:00:00' AND instalation_date <= '$waveTime') OR
					(instalation_date  = '0000-00-00 00:00:00' AND removing_date != '0000-00-00 00:00:00' AND removing_date >= '$waveTime') OR
					(instalation_date != '0000-00-00 00:00:00' AND removing_date != '0000-00-00 00:00:00' AND instalation_date <= '$waveTime' AND removing_date >= '$waveTime')
				)";

		//echo "/* ttt  +++++ ".$sql." */";

		$stationDetails = mysql_query($sql);
		//შევამოწმოთ თუ მოიძებნა ასეთი სადგურის დეტალი
		if(mysql_num_rows($stationDetails) > 0){
			//თუ მოიძებნა წავიკითხოთ სადგურის id
			$stationDetail = mysql_fetch_array($stationDetails);
			$stationId = $stationDetail["station_id"];
		}else{ //ალტერნატიული კოდით თუ არ მოიძებნა სადგურის დეტალი მაშინ მოვძებნოთ სადგურის კოდით
			$sql = "SELECT stations.id FROM stations
					LEFT JOIN stations_details ON stations.id = stations_details.station_id
					WHERE stations.code = '$stationCode' AND network_code = '$networkCode' AND location_code = '$locationCode' AND (
					(instalation_date  = '0000-00-00 00:00:00' AND removing_date  = '0000-00-00 00:00:00') OR 
					(instalation_date != '0000-00-00 00:00:00' AND removing_date  = '0000-00-00 00:00:00' AND instalation_date <= '$waveTime') OR
					(instalation_date  = '0000-00-00 00:00:00' AND removing_date != '0000-00-00 00:00:00' AND removing_date >= '$waveTime') OR
					(instalation_date != '0000-00-00 00:00:00' AND removing_date != '0000-00-00 00:00:00' AND instalation_date <= '$waveTime' AND removing_date >= '$waveTime')
				)";

			$stationDetails = mysql_query($sql);
			//შევამოწმოთ თუ მოიძებნა ასეთი სადგური
			if(mysql_num_rows($stationDetails) > 0){
			//თუ მოიძებნა წავიკითხოთ სადგურის id
				$stationDetail = mysql_fetch_array($stationDetails);
				$stationId = $stationDetail["id"];
			}
		}
	}else{


		$sql = "SELECT station_id, network_code, alternative_code, location_code, instalation_date, removing_date FROM stations_details WHERE alternative_code='$stationCode' ORDER BY instalation_date DESC";
		//echo "<br>";
		$stationDetails = mysql_query($sql);

		while($stationDetail = mysql_fetch_array($stationDetails))
		{
			
			$instalationDate = $stationDetail['instalation_date'];
			
			if($stationDetail['removing_date'] == '0000-00-00 00:00:00') $removingDate = '2037-01-19 04:14:07';
			else $removingDate = $stationDetail['removing_date'];
			
			if (millisecsBetween($waveTime , $instalationDate, false) > 0 and millisecsBetween($removingDate , $waveTime, false) > 0)
			{
				$networkCode = $stationDetail['network_code'];
				$locationCode = $stationDetail['location_code'];
				$stationId = $stationDetail["station_id"];
				break;
			}
		}
		
		if($networkCode == "")
		{
			$stationDetails = mysql_query("SELECT stations.id, network_code, stations.code, stations_details.location_code, stations_details.instalation_date, stations_details.removing_date 
										   FROM stations 
										   INNER JOIN stations_details ON stations.id = stations_details.station_id
							               WHERE code='$stationCode' ORDER BY instalation_date  DESC");
			while($stationDetail = mysql_fetch_array($stationDetails))
			{
				$instalationDate = $stationDetail['instalation_date'];
				
				if($stationDetail['removing_date'] == '0000-00-00 00:00:00') $removingDate = '2037-01-19 04:14:07';
				else $removingDate = $stationDetail['removing_date'];
										
				if (millisecsBetween($waveTime , $instalationDate, false) > 0 and millisecsBetween($removingDate , $waveTime, false) > 0)
				{
					$networkCode = $stationDetail['network_code'];
					$locationCode = $stationDetail['location_code'];
					$stationId = $stationDetail["id"];
					break;
				}
			}
		}
	}
	
	if($stationId == "")
	{
		if($errorStationList == "") $errorStationList = $stationCode;
		else $errorStationList .= ", ".$stationCode;
	}

	?>
	
	
	 if(typeof primaries[stName] == 'undefined')
		 primaries[stName] = new Array();
     primaries[stName]['networkCode'] = '<?php echo $networkCode?>';
	 primaries[stName]['locationCode'] = '<?php echo $locationCode?>';
	 primaries[stName]['hypocenterDistance'] = '<?php if(isset($_POST[$STnum."distance"])) echo $_POST[$STnum."distance"];?>'; 
	 primaries[stName]['azimute'] = '<?php if(isset($_POST[$STnum."azimuth"])) echo $_POST[$STnum."azimuth"];?>';
	 primaries[stName]['rezOriginTimeP'] = '<?php if(isset($_POST[$STnum."residual_origin_time_p"])) echo $_POST[$STnum."residual_origin_time_p"];?>';
	 primaries[stName]['rezOriginTimeS'] = '<?php if(isset($_POST[$STnum."residual_origin_time_s"])) echo $_POST[$STnum."residual_origin_time_s"];?>';
	 primaries[stName]['usedForCalculation'] = '<?php if(isset($_POST[$STnum."used_for_calculation"])) echo $_POST[$STnum."used_for_calculation"];?>';


	<?php
	$waveLength = $_POST[$STnum."waveLength"];
	for ($j = 0; $j < $waveLength; $j++)
	{
		$wvNum = "wave".$j."_";
	?>
		waveName = convertWaveName('<?php echo $_POST[$STnum.$wvNum."name"]?>');
		
		if('error' != waveName)
		{
			postWaveNames[waveName] = true;
			if(typeof primaries[stName]['waves'] == 'undefined')
				primaries[stName]['waves'] = new Array();
			
			if(typeof primaries[stName]['waves'][waveName] == 'undefined')
				primaries[stName]['waves'][waveName] = new Array();
			primaries[stName]['waves'][waveName]['time'] = '<?php echo SHMtimeToPhpPlusMsec($_POST[$STnum.$wvNum."time"]);?>'
			primaries[stName]['waves'][waveName]['onsetType'] = '<?php if(isset($_POST[$STnum.$wvNum."onsetType"])) echo $_POST[$STnum.$wvNum."onsetType"];?>';
			primaries[stName]['waves'][waveName]['quality'] = '<?php if(isset($_POST[$STnum.$wvNum."quality"])) echo $_POST[$STnum.$wvNum."quality"];?>';
			primaries[stName]['waves'][waveName]['weight'] = '<?php if(isset($_POST['soft']) and $_POST['soft'] == 'LocSAT(SHM)') echo $_POST[$STnum.$wvNum."quality"]; else echo $_POST[$STnum.$wvNum."weight"];?>' ;
			primaries[stName]['waves'][waveName]['usedForCalculation'] = '<?php if (isset($_POST[$STnum.$wvNum."used_for_calculation"])) echo $_POST[$STnum.$wvNum."used_for_calculation"];?>';
			<?php
			$compLength = $_POST[$STnum.$wvNum."compLength"];
			for ($k = 0; $k < $compLength; $k++)
			{
				$compNum = "comp".$k."_";
				?>
				compName = '<?php echo $_POST[$STnum.$wvNum.$compNum."name"];?>';
				primaries[stName]['waves'][waveName]['sign'+compName] = '<?php echo $_POST[$STnum.$wvNum.$compNum."sign"];?>';
				<?php
				if(isset($_POST[$STnum.$wvNum.$compNum."amplitude"]))
				{
				?>
					if(typeof primaries[stName]['amplitudes'] == 'undefined')
						primaries[stName]['amplitudes'] = new Array();
					if(typeof primaries[stName]['amplitudes'][waveName] == 'undefined')
						primaries[stName]['amplitudes'][waveName] = new Array();
					


					var amplitude_shm_scale = <?php echo $amplitude_shm_scale = isset($_POST['submited_from_shm']) ? 1000000 : 1; ?>;
					


					primaries[stName]['amplitudes'][waveName][compName] = new Array();
					primaries[stName]['amplitudes'][waveName][compName]['value'] = <?php if (isset($_POST[$STnum.$wvNum.$compNum."amplitude"]) and $_POST[$STnum.$wvNum.$compNum."amplitude"] != '') echo "parseFloat(".$_POST[$STnum.$wvNum.$compNum."amplitude"].")/amplitude_shm_scale"; else echo "''"; ?>;
					primaries[stName]['amplitudes'][waveName][compName]['dominantPeriod'] = '<?php echo $_POST[$STnum.$wvNum.$compNum."period"];?>';
					primaries[stName]['amplitudes'][waveName][compName]['time'] = '<?php echo $_POST[$STnum.$wvNum.$compNum."amplitudeTime"];?>';
					primaries[stName]['amplitudes'][waveName][compName]['velocity'] = <?php if (isset($_POST[$STnum.$wvNum.$compNum."amplitudeVel"]) and $_POST[$STnum.$wvNum.$compNum."amplitudeVel"] != '') echo "parseFloat(".$_POST[$STnum.$wvNum.$compNum."amplitudeVel"].")/amplitude_shm_scale"; else echo "''"; ?>;
					primaries[stName]['amplitudes'][waveName][compName]['program'] = '<?php if (isset($_POST[$STnum.$wvNum.$compNum."program"])) echo $_POST[$STnum.$wvNum.$compNum."program"];?>';



				<?php
				}
			}
			?>
			if(typeof primaries[stName]['waves'][waveName]['signE'] == 'undefined')	primaries[stName]['waves'][waveName]['signE'] = '';
			if(typeof primaries[stName]['waves'][waveName]['signN'] == 'undefined')	primaries[stName]['waves'][waveName]['signN'] = '';
			if(typeof primaries[stName]['waves'][waveName]['signZ'] == 'undefined')	primaries[stName]['waves'][waveName]['signZ'] = '';
		}
	<?php
	}
	?>
	var firstWaveName = getFirstWaveName(stName);
	if(firstWaveName == 'none')
		alert(stName+'-ს არ აქვს არცერთი ტალღა დამატებული')
	primaries[stName]['signE'] = primaries[stName]['waves'][firstWaveName]['signE'];
	primaries[stName]['signN'] = primaries[stName]['waves'][firstWaveName]['signN'];
	primaries[stName]['signZ'] = primaries[stName]['waves'][firstWaveName]['signZ'];

	<?php
	$magLength = $_POST[$STnum."magLength"];
	

	for ($j = 0; $j < $magLength; $j++)
	{
		$mgNum = "mag".$j."_";		
	?>
		magName = convertMagName('<?php echo $_POST[$STnum.$mgNum."name"]?>');
		if('error' != magName)
		{
			if(typeof primaries[stName]['magnitudes'] == 'undefined')
				primaries[stName]['magnitudes'] = new Array();
			if(typeof primaries[stName]['magnitudes'][magName] == 'undefined')
				primaries[stName]['magnitudes'][magName] = new Array();
			primaries[stName]['magnitudes'][magName]['value'] = '<?php if(isset($_POST[$STnum.$mgNum."value"])) echo $_POST[$STnum.$mgNum."value"];?>';
			primaries[stName]['magnitudes'][magName]['residual'] = '<?php if(isset($_POST[$STnum.$mgNum."residual"])) echo $_POST[$STnum.$mgNum."residual"];?>';
		}
	<?php
	}
}

?>
postEq['stationMinDistance'] = getStationMinDistance();
postEq['magnitudes'] = new Array();
<?php
	$postEqMagLength = $_POST["EQ_magLength"];
	for ($i = 0; $i < $postEqMagLength; $i++)
	{
		$magName = "EQ_mag".$i."_";
		
?>
		magName = convertMagName('<?php echo $_POST[$magName."name"]?>');
		if('error' != magName)
		{
			if(typeof postEq['magnitudes'][magName] == 'undefined')
				postEq['magnitudes'][magName] = new Array();
			postEq['magnitudes'][magName]['value'] = '<?php if (isset($_POST[$magName."value"])) echo $_POST[$magName."value"];?>';
			postEq['magnitudes'][magName]['maxValue'] = '<?php if (isset($_POST[$magName."max"])) echo $_POST[$magName."max"];?>';
			postEq['magnitudes'][magName]['minValue'] = '<?php if (isset($_POST[$magName."min"])) echo $_POST[$magName."min"];?>';
			postEq['magnitudes'][magName]['uncertainty'] = '<?php if (isset($_POST[$magName."uncertainty"])) echo $_POST[$magName."uncertainty"];?>';
			postEq['magnitudes'][magName]['stationCount'] = '<?php if (isset($_POST[$magName."number"])) echo $_POST[$magName."number"];?>';		
		}
<?php
	}
	
	
?>                                 

var errorStationList = '<?php echo $errorStationList;?>';



</script>
</head>
<script>
</script>
<body onload="OnLoad('<?php if(isset($_POST['EQ_time'])) echo SHMtimeToPhpPlusMsec($_POST['EQ_time']); else echo "";?>')">
<?php include("../block/mainmenu.php");?>
<div id="ajaxLoader" class="ajaxLoader">
<img src="../images/ajaxLoader.gif"/>
</div>
<table width="100%" border="0" style="width:100%;padding-top:10px;">
  <tr>
    <td align="center">
    	<input id="soft" type="hidden" value="<?php if(isset($_POST['soft'])) echo $_POST['soft'];?>"/>
		<input id="eqOriginTime" type="hidden" value="<?php if(isset($_POST['EQ_time'])) echo SHMtimeToPhpPlusMsec($_POST['EQ_time']);?>"/>
        <input id="eqLatitude" type="hidden" value="<?php if(isset($_POST['EQ_latitude'])) echo $_POST['EQ_latitude'];?>"/>
        <input id="eqLongitude" type="hidden" value="<?php if(isset($_POST['EQ_longitude'])) echo $_POST['EQ_longitude'];?>"/>
        <input id="eqDepth" type="hidden" value="<?php if(isset($_POST['EQ_depth'])) echo $_POST['EQ_depth']?>"/>
        <input id="eqTimeHypocenterProgram" type="hidden" value="<?php if(isset($_POST['soft'])) echo $_POST['soft'];?>"/>

        <input id="eqMl" type="hidden" value="<?php if(isset($_POST['EQ_ml'])) echo $_POST['EQ_ml'];?>"/>
		<input id="eqMlMinValue" type="hidden" value="<?php if(isset($_POST['ml_min'])) echo $_POST['ml_min'];?>"/>  
        <input id="eqMlMaxValue" type="hidden" value="<?php if(isset($_POST['ml_max'])) echo $_POST['ml_max'];?>"/>	
        <input id="eqMlStationCount" type="hidden" value="<?php if(isset($_POST['ml_count'])) echo $_POST['ml_count'];?>"/>
        <input id="eqMlProgram" type="hidden" value="<?php if(isset($_POST['soft'])) echo $_POST['soft'];?>"/>
        
        <input id="eqStationRecordCount" type="hidden" value="<?php if(isset($_POST['ST_number'])) echo $_POST['ST_number'];?>"/>
        <?php
        if(isset($_POST['submited_from_shm'])){
        	if(isset($_POST['EQ_time']) && $_POST['EQ_time'] != "" && isset($_POST['ST_number'])){
        		$eqStationUsedCount = $_POST['ST_number'];
        	}else{
        		$eqStationUsedCount = "";
        	}
        }else if(isset($_POST["EQ_station_used_count"])){
        	$eqStationUsedCount = $_POST['EQ_station_used_count'];
        }else{
        		$eqStationUsedCount = "";
        }
        ?>
        <input id="eqStationUsedCount" type="hidden" value="<?php echo $eqStationUsedCount ;?>"/> 

<?php




		if(isset($_POST['EQ_phases_count'])){
			$eqPhasesCount = $_POST['EQ_phases_count'];
		}else if(isset($_POST['EQ_phases_used_count'])){
			$eqPhasesCount = $_POST['EQ_phases_count'];
		}else{
			$eqPhasesCount = "";
		}

?>
        <input id="eqPhasesCount" type="hidden" value="<?php echo $eqPhasesCount;?>"/>
        <input id="eqPhasesUsedCount" type="hidden" value="<?php if(isset($_POST['EQ_phases_used_count'])) echo $_POST['EQ_phases_used_count'];?>"/>
        
        <input id="eqGap" type="hidden" value="<?php if(isset($_POST['EQ_max_azimuthal_gap'])) echo $_POST['EQ_max_azimuthal_gap'];?>"/>
       <!-- <input id="eqStationMinDistance" type="hidden" value=""/>-->
        
		<input id="eqTimeUncertainty" type="hidden" value="<?php if(isset($_POST['EQ_rms'])) echo $_POST['EQ_rms'];?>"/>
        <input id="eqHorizontalUncertainty" type="hidden" value="<?php if(isset($_POST['EQ_epicenter_uncertainty'])) echo $_POST['EQ_epicenter_uncertainty'];?>"/> <!--chasascorebelia-->
        <input id="eqDepthUncertainty" type="hidden" value="<?php if(isset($_POST['EQ_err_depth'])) echo $_POST['EQ_err_depth'];?>"/>
        <input id="eqLatitudeUncertainty" type="hidden" value="<?php if(isset($_POST['EQ_err_lat'])) echo $_POST['EQ_err_lat'];?>"/>
        <input id="eqLongitudeUncertainty" type="hidden" value="<?php if(isset($_POST['EQ_err_long'])) echo $_POST['EQ_err_long'];?>"/>

        <input id="eqShakeSource" type="hidden" value="<?php if(isset($_POST['EQ_event_type'])) echo $_POST['EQ_event_type'];?>"/>
        <input id="eqArea" type="hidden" value="<?php if(isset($_POST['EQ_area'])) echo $_POST['EQ_area'];?>"/>
        <input id="eqIntencity" type="hidden" value="<?php if(isset($_POST['EQ_intencity'])) echo $_POST['EQ_intencity'];?>"/>


        <input id="eqRegionGe" type="hidden" value="<?php if(isset($_POST['EQ_region_ge'])) echo htmlspecialchars($_POST['EQ_region_ge']);?>"/>
        <input id="eqRegionEn" type="hidden" value="<?php if(isset($_POST['EQ_region_en'])) echo htmlspecialchars($_POST['EQ_region_en']);?>"/>
        <input id="eqInfoGe" type="hidden" value="<?php if(isset($_POST['EQ_about_earthquake_ge'])) echo htmlspecialchars($_POST['EQ_about_earthquake_ge']);?>"/>
        <input id="eqInfoEn" type="hidden" value="<?php if(isset($_POST['EQ_about_earthquake_en'])) echo htmlspecialchars($_POST['EQ_about_earthquake_en']);?>"/>
        <input id="eqComment" type="hidden" value="<?php if(isset($_POST['EQ_comment'])) echo htmlspecialchars($_POST['EQ_comment']);?>"/>

        <input id="eqImportant" type="hidden" value="<?php if(isset($_POST['EQ_important'])) echo $_POST['EQ_important'];?>"/>
		<input id="eqVmId" type="hidden" value="<?php if(isset($_POST['EQ_velocity_model_id'])) echo $_POST['EQ_velocity_model_id'];?>"/>
        
       




            <div id="sameEqsLabel" style="color:#F03; height:20px;font-style:italic;">ქვემოთ მოცემულია დასამატებელი მიწისძვრის მონაცემები და ამ მიწისძვრის კერის დროსთან ახლოს მდებარე ბაზაში არსებული მიწისძვრები</div>
			<table id="sameEqsTable" width="100%" border="0" cellspacing="0" class="wavesTable" style="text-align:center;width:700px; margin-bottom:0px">
              <tr class="wavesNamePandS">
                <td colspan="8">დასამატებელი მიწისძვრის მონაცემები</td>
              </tr>
              <tr class="wavesLabels">
                <td style="border-bottom:1px #CCC solid;"></td>
                <td class="wavesLabel">კერის დრო</td>
                <td class="wavesLabel">განედი</td>
                <td class="wavesLabel">გრძედი</td>
                <td class="wavesLabel">ML</td>
                <td class="wavesLabel" style="width:120px;">სადგურები(რაოდ)</td>
                <td class="wavesLabel" style="width:120px;">ადგილმდებარეობა</td>
                <td class="wavesLabel">პროგრამა</td>
              </tr>
              <tr style="height:40px;">
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
              </tr>
              <tr class="wavesNamePandS">
                <td colspan="8">ბაზაში არსებული მიწისძვრები</td>
              </tr>
              <tr class="wavesLabels">
                <td style="border-bottom:1px #CCC solid;"></td>
                <td class="wavesLabel">კერის დრო</td>
                <td class="wavesLabel">განედი</td>
                <td class="wavesLabel">გრძედი</td>
                <td class="wavesLabel">ML</td>
                <td class="wavesLabel">სადგურები(რაოდ)</td>
                <td class="wavesLabel">ადგილმდებარეობა</td>
                <td class="wavesLabel">პროგრამა</td>
              </tr>
            </table>
            <div id="eqLabel" style="color:#F03; font-style:italic;display:none;">წითლად ნაჩვენებია მიწისძვრის და პირველადების მონაცემები, რომლებიც შეიძლება წაიშალოს განახლების შემთხვევაში.<br/> მონიშნეთ ის მონაცემები რომლებიც უნდა ჩაემატოს ან განახლდეს მონაცემთა ბაზაში.</div><br />
			<table id="sameEqTable" border="0" cellspacing="0" class="wavesTable" style="text-align:center;display:none;">
              <tr class="wavesNamePandS">
                <td colspan="13">დასამატებელი მიწისძვრის მონაცემები</td>
              </tr>
              <tr class="wavesLabels">
              	<td style="border-bottom:1px #CCC solid;width:60px;">მონიშვნა</td>
                <td class="wavesLabel">კერის დრო</td>
                <td class="wavesLabel" style="width:50px;">განედი</td>
                <td class="wavesLabel" style="width:50px;">გრძედი</td>
                <td class="wavesLabel" style="width:50px;">სიღრმე</td>
                <td class="wavesLabel" style="width:60px;">პროგრამა</td>
                <td class="wavesLabel" style="width:65px;">სადგურები</td>
                <td class="wavesLabel" style="width:90px;">გამოყენებული<br/>სადგურები</td>
                <td class="wavesLabel" style="width:35px;">გაფი</td>
                <td class="wavesLabel" style="width:110px;">მანძილი უახლოეს სადგურამდე</td>
                <td class="wavesLabel" style="width:35px;">ML</td>
                <td class="wavesLabel" style="width:80px;">ML<br/>(ცდომილება)</td>
                <td class="wavesLabel" style="width:115px;">ადგილმდებარეობა</td>
              </tr>
              <tr style="height:35px;color:#F03;font-weight:bold;">
                <td><input id="eqCheckbox" type="checkbox" onchange="javascript:onCheckboxCheck(this)" /></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
              </tr>
              <tr class="wavesNamePandS">
                <td colspan="13">ბაზაში არსებული მიწისძვრის მონაცემები</td>
              </tr>
<!--              <tr class="wavesLabels">
                <td style="border-bottom:1px #CCC solid;"></td>
                <td class="wavesLabel">კერის დრო</td>
                <td class="wavesLabel">განედი</td>
                <td class="wavesLabel">გრძედი</td>
                <td class="wavesLabel">სიღრმე</td>
                <td class="wavesLabel">პროგრამა</td>
                <td class="wavesLabel">სადგურები</td>
                <td class="wavesLabel">გამოყენებული სადგურები</td>
                <td class="wavesLabel">გაფი</td>
                <td class="wavesLabel">მანძილი უახლოეს სადგურამდე</td>
                <td class="wavesLabel">ML</td>
                <td class="wavesLabel">ML ცდომილება</td>
                <td class="wavesLabel">ადგილმდებარეობა</td>
              </tr>-->
              <tr style="height:35px;color:#F03;font-weight:bold;">
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
              </tr>
            </table><br />
			<table id="samePrimariesTable" border="0" cellspacing="0" class="wavesTable" style="text-align:center;display:none;">
              <tr class="wavesNamePandS" id="samePrimariesTablePostHeader">
                <td colspan="12">დასამატებელი პირველადების მონაცემები</td>
              </tr>
              <tr></tr>
              <tr class="wavesNamePandS" id="samePrimariesTableDatabaseHeader">
                <td colspan="12">ბაზაში არსებული პირველადების მონაცემები</td>
              </tr>
            </table>  
            <div id="eqsButtons" style="width:800px;margin-bottom:60px; margin-top:-10px;">
                <div class="linkBtn" onclick="javascript:saveEqAndPrimaries();" style="padding-left:0px;width:160px;">
                    <img src="../images/eq/submit.png" align="absmiddle"/>
                    ახლის დამატება
                </div>
                <div class="splitDiv"></div>
                <div class="linkBtn" onclick="javascript:closePostEqWindow();" style="padding-left:0px;width:160px;">
                    <img src="../images/eq/close.png" align="absmiddle"/>
                    ფანჯრის დახურვა
                </div>
            </div>
          	<div id="eqPrimarybuttons" style="width:800px;margin-bottom:60px;display:none;">
                <div class="linkBtn" onclick="javascript:checkAll();" style="padding-left:0px;width:180px;">
                    <img src="../images/eq/check_all.png" align="absmiddle"/>
                    მონიშნე ყველა/არცერთი
                </div>
                <div class="splitDiv"></div>
                <div class="linkBtn" onclick="javascript:updateEqAndPrimaries();" style="padding-left:0px;width:130px;">
                    <img src="../images/eq/update.png" align="absmiddle"/>
                    განახლება
                </div>
                <div class="splitDiv"></div>
                <div class="linkBtn" onclick="javascript:Back();" style="padding-left:0px;width:130px;">
                    <img src="../images/eq/back.png" align="absmiddle"/>
                    უკან
                </div>
			</div>
    </td>
  </tr>
</table>
    </td>
  </tr>
</table>
</body>
</html>
