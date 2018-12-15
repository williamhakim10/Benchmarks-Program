const 
	interestsForm = document.querySelector('#interest-groups-form');

if (interestsForm) {
	const
		analyzeWholeList = interestsForm.querySelector('#analyze_whole_list'),
		interestGroupsSection = interestsForm.querySelector('#interest-groups');
	analyzeWholeList.addEventListener(
		'change', () => toggleDisabled(interestGroupsSection))
}