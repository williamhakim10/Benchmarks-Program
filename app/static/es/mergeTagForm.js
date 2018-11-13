const mergeForm = document.querySelector('#merge-tags-form');

/* Submit merge tags */
const submitMergeTags = async e => {
	e.preventDefault();
	mergeForm.removeEventListener('submit', submitMergeTags);
	const formElts = mergeForm.querySelectorAll('select, input');
	disable(formElts);
	const
		formData = new formData(mergeForm),
		request = fetchRequest('/validate-merge-tags', formData);
	try {
		const response = await fetch(request);
		if (response.ok)
			console.error('ok');
		else {
			if (response.status == 422)
				console.error('form error');
			else
				throw new Error(response.statusText);
		}
	}
	catch(e) {
		console.error(e)
	}
}

if (mergeForm) {
	let rows = 0;
	const
		addRowLink = mergeForm.querySelector('#add-merge-item'),
		rowHtmlStr = mergeForm.querySelector(
			'.merge-tags-form-item').outerHTML;
	addRowLink.addEventListener('click', () => {
		++rows;
		const
			newRow = rowHtmlStr.replace(/0/g, rows),
			items = mergeForm.querySelectorAll('.merge-tags-form-item'),
			lastItem = items[items.length - 1];
		lastItem.insertAdjacentHTML('afterend', newRow);
	})
}