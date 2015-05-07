
Feature: Test the drive manager sensor and DCS-Collector
	Manipulate the /var/run/diskmonitor file and verify
	that the DCS-Collector/OpenHPI combination correctly
	populates the /tmp/dcs/drivemanager which SSPL-LL
	monitors with Inotify and generates JSON responses

Scenario: Change the first drive to inuse_failed status and examine response
	Given that all drives are set to "inuse_ok" and sspl is started
	When I set the "first_drive" to "inuse_failed" with serial number "S0M29BHS0000B429FX6M"
	Then SSPL_LL transmits a JSON msg with status inuse_failed for disk number "0" and enc "SHU0951732G1GXC"

Scenario: Change the middle drive to inuse_failed status and examine response
	Given that all drives are set to "inuse_ok" and sspl is started
	When I set the "middle_drive" to "inuse_failed" with serial number "S0M29BVE0000M434WP39"
	Then SSPL_LL transmits a JSON msg with status inuse_failed for disk number "13" and enc "SHU0951732G1GXC"

Scenario: Change the last drive to inuse_failed status and examine response
	Given that all drives are set to "inuse_ok" and sspl is started
	When I set the "last_drive" to "inuse_failed" with serial number "S0M29JES0000B435AKVM"
	Then SSPL_LL transmits a JSON msg with status inuse_failed for disk number "23" and enc "SHU0951732G1GXC"

Scenario: Change 5 drives to inuse_failed status and examine all responses
	Given that all drives are set to "inuse_ok" and sspl is started
	When I set "5" drives to "inuse_failed"
	Then SSPL_LL transmits JSON msgs with status "inuse_failed" for "5" drives for enclosure "SHU0951732G1GXC"

Scenario: Change 5 drives to inuse_ok status and examine all responses
	Given that all drives are set to "inuse_failed" and sspl is started
	When I set "5" drives to "inuse_ok"
	Then SSPL_LL transmits JSON msgs with status "inuse_ok" for "5" drives for enclosure "SHU0951732G1GXC"
