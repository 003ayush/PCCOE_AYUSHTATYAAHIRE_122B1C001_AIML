"""Build threat_library.json verbatim from UN R155 Annex 5 (Official Journal L 82, 9.3.2021, CELEX 42021X0387).

Threat text = Table A1; mitigation text = Tables B1-B8 / C1-C3. Only `stride_category` and
`typical_assets` are our annotations (Annex 5 does not provide them).
"""
import json
from pathlib import Path

# Package root (PCCOE_StudentName_PRN_CSx_AIML) derived from this file's location.
OUT = Path(__file__).resolve().parents[2] / "Input_Data" / "threat_library.json"

M = {  # official mitigation wording
    "M1": "Security Controls are applied to back-end systems to minimise the risk of insider attack",
    "M2": "Security Controls are applied to back-end systems to minimise unauthorised access. Example Security Controls can be found in OWASP",
    "M3": "Security Controls are applied to back-end systems. Where back-end servers are critical to the provision of services there are recovery measures in case of system outage. Example Security Controls can be found in OWASP",
    "M4": "Security Controls are applied to minimise risks associated with cloud computing. Example Security Controls can be found in OWASP and NCSC cloud computing guidance",
    "M5": "Security Controls are applied to back-end systems to prevent data breaches. Example Security Controls can be found in OWASP",
    "M6": "Systems shall implement security by design to minimize risks",
    "M7": "Access control techniques and designs shall be applied to protect system data/code. Example Security Controls can be found in OWASP",
    "M8": "Through system design and access control it should not be possible for unauthorized personnel to access personal or system critical data. Example of Security Controls can be found in OWASP",
    "M9": "Measures to prevent and detect unauthorized access shall be employed",
    "M10": "The vehicle shall verify the authenticity and integrity of messages it receives",
    "M11": "Security controls shall be implemented for storing cryptographic keys (e.g., use of Hardware Security Modules)",
    "M12": "Confidential data transmitted to or from the vehicle shall be protected",
    "M13": "Measures to detect and recover from a denial of service attack shall be employed",
    "M14": "Measures to protect systems against embedded viruses/malware should be considered",
    "M15": "Measures to detect malicious internal messages or activity should be considered",
    "M16": "Secure software update procedures shall be employed",
    "M18": "Measures shall be implemented for defining and controlling user roles and access privileges, based on the principle of least access privilege",
    "M19": "Organizations shall ensure security procedures are defined and followed including logging of actions and access related to the management of the security functions",
    "M20": "Security controls shall be applied to systems that have remote access",
    "M21": "Software shall be security assessed, authenticated and integrity protected. Security controls shall be applied to minimise the risk from third party software that is intended or foreseeable to be hosted on the vehicle",
    "M22": "Security controls shall be applied to external interfaces",
    "M23": "Cybersecurity best practices for software and hardware development shall be followed",
    "M24": "Best practices for the protection of data integrity and confidentiality shall be followed for storing personal data",
}

# Table A1 high-level threats (verbatim)
P = {
    1: "Back-end servers used as a means to attack a vehicle or extract data",
    2: "Services from back-end server being disrupted, affecting the operation of a vehicle",
    3: "Vehicle related data held on back-end servers being lost or compromised ('data breach')",
    4: "Spoofing of messages or data received by the vehicle",
    5: "Communication channels used to conduct unauthorized manipulation, deletion or other amendments to vehicle held code/data",
    6: "Communication channels permit untrusted/unreliable messages to be accepted or are vulnerable to session hijacking/replay attacks",
    7: "Information can be readily disclosed. For example, through eavesdropping on communications or through allowing unauthorized access to sensitive files or folders",
    8: "Denial of service attacks via communication channels to disrupt vehicle functions",
    9: "An unprivileged user is able to gain privileged access to vehicle systems",
    10: "Viruses embedded in communication media are able to infect vehicle systems",
    11: "Messages received by the vehicle (for example X2V or diagnostic messages), or transmitted within it, contain malicious content",
    12: "Misuse or compromise of update procedures",
    13: "It is possible to deny legitimate updates",
    15: "Legitimate actors are able to take actions that would unwittingly facilitate a cyberattack",
    16: "Manipulation of the connectivity of vehicle functions enables a cyberattack, this can include telematics; systems that permit remote operations; and systems using short range wireless communications",
    17: "Hosted 3rd party software, e.g. entertainment applications, used as a means to attack vehicle systems",
    18: "Devices connected to external interfaces e.g. USB ports, OBD port, used as a means to attack vehicle systems",
    19: "Extraction of vehicle data/code",
    20: "Manipulation of vehicle data/code",
    21: "Erasure of data/code",
    22: "Introduction of malware",
    23: "Introduction of new software or overwrite existing software",
    24: "Disruption of systems or operations",
    25: "Manipulation of vehicle parameters",
    26: "Cryptographic technologies can be compromised or are insufficiently applied",
    27: "Parts or supplies could be compromised to permit vehicles to be attacked",
    28: "Software or hardware development permits vulnerabilities",
    29: "Network design introduces vulnerabilities",
    31: "Unintended transfer of data can occur",
    32: "Physical manipulation of systems can enable an attack",
}

# Asset names used in asset_catalogue.json (our synthetic TCU assets)
FW, KEY, TEL, CAN, LOG, BOOT, PII, DIAG, CMD, CELL, GNSS, APP = (
    "Firmware Update Package", "Cryptographic Keys", "Telemetry Data", "Vehicle CAN Bus",
    "Security Event Logs", "Boot Configuration and Root of Trust", "Personal Data",
    "Diagnostic Interface", "Remote Command Channel", "Cellular Connectivity Service",
    "Positioning Data (GNSS)", "Stored Application Software")

# ref: (sub-level verbatim text, STRIDE (annotation), assets (annotation), mitigation ids)
T = {
    "1.1": ("Abuse of privileges by staff (insider attack)", "Elevation of Privilege", [CMD, FW, KEY], ["M1"]),
    "1.2": ("Unauthorized internet access to the server (enabled for example by backdoors, unpatched system software vulnerabilities, SQL attacks or other means)", "Elevation of Privilege", [CMD, FW, TEL], ["M2"]),
    "2.1": ("Attack on back-end server stops it functioning, for example it prevents it from interacting with vehicles and providing services they rely on", "Denial of Service", [CMD, TEL, CELL], ["M3"]),
    "3.2": ("Loss of information in the cloud. Sensitive data may be lost due to attacks or accidents when data is stored by third-party cloud service providers", "Information Disclosure", [TEL, PII], ["M4"]),
    "3.3": ("Unauthorized internet access to the server (enabled for example by backdoors, unpatched system software vulnerabilities, SQL attacks or other means)", "Information Disclosure", [TEL, PII], ["M2"]),
    "3.5": ("Information breach by unintended sharing of data (e.g. admin errors)", "Information Disclosure", [TEL, PII], ["M5"]),
    "4.1": ("Spoofing of messages by impersonation (e.g. 802.11p V2X during platooning, GNSS messages, etc.)", "Spoofing", [GNSS, CMD, TEL], ["M10"]),
    "5.1": ("Communications channels permit code injection, for example tampered software binary might be injected into the communication stream", "Tampering", [FW, APP], ["M10", "M6"]),
    "5.2": ("Communications channels permit manipulate of vehicle held data/code", "Tampering", [APP, TEL], ["M7"]),
    "5.3": ("Communications channels permit overwrite of vehicle held data/code", "Tampering", [APP, FW], ["M7"]),
    "5.4": ("Communications channels permit erasure of vehicle held data/code", "Tampering", [APP, LOG], ["M7"]),
    "5.5": ("Communications channels permit introduction of data/code to the vehicle (write data code)", "Tampering", [APP, FW], ["M7"]),
    "6.1": ("Accepting information from an unreliable or untrusted source", "Spoofing", [CMD, CELL], ["M10"]),
    "6.2": ("Man in the middle attack/ session hijacking", "Spoofing", [CMD, TEL, CELL], ["M10"]),
    "6.3": ("Replay attack, for example an attack against a communication gateway allows the attacker to downgrade software of an ECU or firmware of the gateway", "Spoofing", [CMD, FW], ["M10"]),
    "7.1": ("Interception of information / interfering radiations / monitoring communications", "Information Disclosure", [TEL, PII, CELL], ["M12"]),
    "7.2": ("Gaining unauthorized access to files or data", "Information Disclosure", [PII, APP, KEY], ["M8"]),
    "8.1": ("Sending a large number of garbage data to vehicle information system, so that it is unable to provide services in the normal manner", "Denial of Service", [CELL, TEL], ["M13"]),
    "9.1": ("An unprivileged user is able to gain privileged access, for example root access", "Elevation of Privilege", [APP, BOOT], ["M9"]),
    "10.1": ("Virus embedded in communication media infects vehicle systems", "Tampering", [APP, FW], ["M14"]),
    "11.1": ("Malicious internal (e.g. CAN) messages", "Tampering", [CAN], ["M15"]),
    "11.3": ("Malicious diagnostic messages", "Tampering", [DIAG, CAN], ["M10"]),
    "11.4": ("Malicious proprietary messages (e.g. those normally sent from OEM or component/system/function supplier)", "Spoofing", [CMD, FW], ["M10"]),
    "12.1": ("Compromise of over the air software update procedures. This includes fabricating the system update program or firmware", "Tampering", [FW, CELL], ["M16"]),
    "12.2": ("Compromise of local/physical software update procedures. This includes fabricating the system update program or firmware", "Tampering", [FW, DIAG], ["M16"]),
    "12.3": ("The software is manipulated before the update process (and is therefore corrupted), although the update process is intact", "Tampering", [FW], ["M16"]),
    "12.4": ("Compromise of cryptographic keys of the software provider to allow invalid update", "Spoofing", [FW, KEY], ["M11"]),
    "13.1": ("Denial of Service attack against update server or network to prevent rollout of critical software updates and/or unlock of customer specific features", "Denial of Service", [FW, CELL], ["M3"]),
    "15.1": ("Innocent victim (e.g. owner, operator or maintenance engineer) being tricked into taking an action to unintentionally load malware or enable an attack", "Spoofing", [APP, DIAG], ["M18"]),
    "15.2": ("Defined security procedures are not followed", "Repudiation", [LOG, KEY], ["M19"]),
    "16.1": ("Manipulation of functions designed to remotely operate systems, such as remote key, immobilizer, and charging pile", "Tampering", [CMD], ["M20"]),
    "16.2": ("Manipulation of vehicle telematics (e.g. manipulate temperature measurement of sensitive goods, remotely unlock cargo doors)", "Tampering", [TEL, CMD], ["M20"]),
    "16.3": ("Interference with short range wireless systems or sensors", "Denial of Service", [CELL, GNSS], ["M20"]),
    "17.1": ("Corrupted applications, or those with poor software security, used as a method to attack vehicle systems", "Elevation of Privilege", [APP], ["M21"]),
    "18.1": ("External interfaces such as USB or other ports used as a point of attack, for example through code injection", "Tampering", [DIAG, APP], ["M22"]),
    "18.2": ("Media infected with a virus connected to a vehicle system", "Tampering", [APP, FW], ["M22"]),
    "18.3": ("Diagnostic access (e.g. dongles in OBD port) used to facilitate an attack, e.g. manipulate vehicle parameters (directly or indirectly)", "Elevation of Privilege", [DIAG, CAN], ["M22"]),
    "19.1": ("Extraction of copyright or proprietary software from vehicle systems (product piracy)", "Information Disclosure", [APP, FW], ["M7"]),
    "19.2": ("Unauthorized access to the owner's privacy information such as personal identity, payment account information, address book information, location information, vehicle's electronic ID, etc.", "Information Disclosure", [PII, TEL], ["M8"]),
    "19.3": ("Extraction of cryptographic keys", "Information Disclosure", [KEY, BOOT], ["M11"]),
    "20.1": ("Illegal/unauthorized changes to vehicle's electronic ID", "Spoofing", [CELL, PII], ["M7"]),
    "20.2": ("Identity fraud. For example, if a user wants to display another identity when communicating with toll systems, manufacturer backend", "Spoofing", [CELL, CMD], ["M7"]),
    "20.3": ("Action to circumvent monitoring systems (e.g. hacking/ tampering/ blocking of messages such as ODR Tracker data, or number of runs)", "Tampering", [TEL, LOG], ["M7"]),
    "20.4": ("Data manipulation to falsify vehicle's driving data (e.g. mileage, driving speed, driving directions, etc.)", "Tampering", [TEL, GNSS], ["M7"]),
    "20.5": ("Unauthorized changes to system diagnostic data", "Tampering", [TEL, DIAG], ["M7"]),
    "21.1": ("Unauthorized deletion/manipulation of system event logs", "Repudiation", [LOG], ["M7"]),
    "22.2": ("Introduce malicious software or malicious software activity", "Elevation of Privilege", [APP, FW], ["M7"]),
    "23.1": ("Fabrication of software of the vehicle control system or information system", "Tampering", [FW, APP, BOOT], ["M7"]),
    "24.1": ("Denial of service, for example this may be triggered on the internal network by flooding a CAN bus, or by provoking faults on an ECU via a high rate of messaging", "Denial of Service", [CAN], ["M13"]),
    "25.1": ("Unauthorized access of falsify the configuration parameters of vehicle's key functions, such as brake data, airbag deployed threshold, etc.", "Tampering", [CAN, APP], ["M7"]),
    "26.1": ("Combination of short encryption keys and long period of validity enables attacker to break encryption", "Information Disclosure", [KEY, TEL], ["M23"]),
    "26.2": ("Insufficient use of cryptographic algorithms to protect sensitive systems", "Information Disclosure", [KEY, TEL], ["M23"]),
    "26.3": ("Using already or soon to be deprecated cryptographic algorithms", "Information Disclosure", [KEY, TEL], ["M23"]),
    "27.1": ("Hardware or software, engineered to enable an attack or fails to meet design criteria to stop an attack", "Tampering", [APP, BOOT], ["M23"]),
    "28.1": ("Software bugs. The presence of software bugs can be a basis for potential exploitable vulnerabilities. This is particularly true if software has not been tested to verify that known bad code/bugs is not present and reduce the risk of unknown bad code/bugs being present", "Elevation of Privilege", [APP, CELL], ["M23"]),
    "28.2": ("Using remainders from development (e.g. debug ports, JTAG ports, microprocessors, development certificates, developer passwords, ...) can permit access to ECUs or permit attackers to gain higher privileges", "Elevation of Privilege", [BOOT, KEY, APP], ["M23"]),
    "29.1": ("Superfluous internet ports left open, providing access to network systems", "Elevation of Privilege", [CELL, APP], ["M23"]),
    "29.2": ("Circumvent network separation to gain control. Specific example is the use of unprotected gateways, or access points (such as truck-trailer gateways), to circumvent protections and gain access to other network segments to perform malicious acts, such as sending arbitrary CAN bus messages", "Elevation of Privilege", [CAN, APP], ["M23"]),
    "31.1": ("Information breach. Personal data may be leaked when the car changes user (e.g. is sold or is used as hire vehicle with new hirers)", "Information Disclosure", [PII], ["M24"]),
    "32.1": ("Manipulation of electronic hardware, e.g. unauthorized electronic hardware added to a vehicle to enable 'man-in-the-middle' attack", "Tampering", [CAN, APP, BOOT], ["M9"]),
}

records = []
for i, (ref, (sub, stride, assets, mits)) in enumerate(T.items(), 1):
    parent = int(ref.split(".")[0])
    records.append({
        "id": f"THREAT-{i:03d}",
        "title": P[parent],
        "description": sub,
        "stride_category": stride,
        "un_r155_reference": f"Annex 5, Part A, Table A1, ref {ref}",
        "typical_assets": assets,
        "standard_mitigations": [f"{m} (Annex 5 Part B/C): {M[m]}" for m in mits],
        # Knowledge lifecycle (PROJECT.md): who mapped the annotations + when.
        "mapping_owner": "TARA team",
        "mapping_review_date": "2026-10-07",
        "mapping_version": 1,
    })

OUT.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(len(records), "threats written")
